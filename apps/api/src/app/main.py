from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.dependencies import CurrentUser, current_user, require_role
from app.models import (
    Customer,
    Order,
    OrderLine,
    PackagingUnit,
    Product,
    SessionRecord,
    Shipment,
    ShipmentLine,
    User,
)
from app.planning import router as planning_router
from app.schemas import (
    CartReplace,
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    HealthOut,
    LoginRequest,
    MeOut,
    MessageOut,
    OrderCreate,
    OrderDetailOut,
    OrderLineCreate,
    OrderLineOut,
    OrderOut,
    OrganizationOut,
    PackagingUnitCreate,
    PackagingUnitOut,
    ProductCreate,
    ProductOut,
    ShipmentCreate,
    ShipmentOut,
)
from app.security import digest, expiry, new_secret, verify_password

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Pallet Building API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type", "X-CSRF-Token", "Idempotency-Key"],
)
app.include_router(planning_router)


@app.exception_handler(IntegrityError)
def integrity_conflict(_: Request, __: IntegrityError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": "CONFLICT"})


@app.get("/api/v1/health/live", response_model=HealthOut, tags=["health"])
def live() -> HealthOut:
    return HealthOut(status="ok", service="api", database="not_checked")


@app.get("/api/v1/health/ready", response_model=HealthOut, tags=["health"])
def ready(db: Session = Depends(get_db)) -> HealthOut:
    db.execute(text("select 1"))
    return HealthOut(status="ok", service="api", database="ok")


@app.post("/api/v1/auth/login", response_model=MeOut, tags=["auth"])
def login(payload: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> MeOut:
    if request.headers.get("origin") != settings.web_origin:
        raise HTTPException(status_code=403, detail="INVALID_ORIGIN")
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS")
    from app.models import Membership, Organization

    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    organization = db.get(Organization, membership.organization_id) if membership else None
    if not membership or not organization:
        raise HTTPException(status_code=403, detail="NO_ORGANIZATION_ACCESS")
    raw_token, raw_csrf = new_secret(), new_secret()
    db.add(SessionRecord(token_hash=digest(raw_token), csrf_hash=digest(raw_csrf), user_id=user.id, organization_id=organization.id, role=membership.role, expires_at=expiry(settings.session_ttl_hours)))
    db.commit()
    response.set_cookie(settings.session_cookie_name, raw_token, httponly=True, secure=settings.app_env == "production", samesite="lax", max_age=settings.session_ttl_hours * 3600)
    response.set_cookie(settings.csrf_cookie_name, raw_csrf, httponly=False, secure=settings.app_env == "production", samesite="lax", max_age=settings.session_ttl_hours * 3600)
    return MeOut(id=user.id, email=user.email, display_name=user.display_name, role=membership.role, organization=OrganizationOut.model_validate(organization), csrf_token=raw_csrf)


@app.post("/api/v1/auth/logout", response_model=MessageOut, tags=["auth"])
def logout(request: Request, response: Response, current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> MessageOut:
    raw = request.cookies.get(settings.session_cookie_name)
    if raw:
        session = db.scalar(select(SessionRecord).where(SessionRecord.token_hash == digest(raw)))
        if session:
            from datetime import UTC, datetime
            session.revoked_at = datetime.now(UTC)
            db.commit()
    response.delete_cookie(settings.session_cookie_name)
    response.delete_cookie(settings.csrf_cookie_name)
    return MessageOut(message="SIGNED_OUT")


@app.get("/api/v1/me", response_model=MeOut, tags=["auth"])
def me(current: CurrentUser = Depends(current_user)) -> MeOut:
    return MeOut(id=current.user.id, email=current.user.email, display_name=current.user.display_name, role=current.role, organization=OrganizationOut.model_validate(current.organization), csrf_token=current.csrf_token)


@app.get("/api/v1/products", response_model=list[ProductOut], tags=["catalog"])
def list_products(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[Product]:
    return list(db.scalars(select(Product).where(Product.organization_id == current.organization.id, Product.is_active.is_(True)).order_by(Product.sku)))


@app.post("/api/v1/products", response_model=ProductOut, status_code=201, tags=["catalog"])
def create_product(payload: ProductCreate, current: CurrentUser = Depends(require_role("admin")), db: Session = Depends(get_db)) -> Product:
    product = Product(organization_id=current.organization.id, sku=payload.sku, name=payload.name)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/api/v1/packaging-units", response_model=list[PackagingUnitOut], tags=["catalog"])
def list_packaging_units(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[PackagingUnit]:
    return list(db.scalars(select(PackagingUnit).where(PackagingUnit.organization_id == current.organization.id).order_by(PackagingUnit.code)))


@app.post("/api/v1/packaging-units", response_model=PackagingUnitOut, status_code=201, tags=["catalog"])
def create_packaging_unit(payload: PackagingUnitCreate, current: CurrentUser = Depends(require_role("admin")), db: Session = Depends(get_db)) -> PackagingUnit:
    product = db.scalar(select(Product).where(Product.id == payload.product_id, Product.organization_id == current.organization.id, Product.is_active.is_(True)))
    if not product:
        raise HTTPException(status_code=404, detail="PRODUCT_NOT_FOUND")
    unit = PackagingUnit(organization_id=current.organization.id, **payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@app.get("/api/v1/customers", response_model=list[CustomerOut], tags=["customers"])
def list_customers(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[Customer]:
    return list(db.scalars(select(Customer).where(Customer.organization_id == current.organization.id).order_by(Customer.name)))


@app.post("/api/v1/customers", response_model=CustomerOut, status_code=201, tags=["customers"])
def create_customer(payload: CustomerCreate, current: CurrentUser = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)) -> Customer:
    customer = Customer(organization_id=current.organization.id, **payload.model_dump())
    db.add(customer)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="CUSTOMER_REFERENCE_CONFLICT") from error
    db.refresh(customer)
    return customer


@app.put("/api/v1/customers/{customer_id}", response_model=CustomerOut, tags=["customers"])
def update_customer(customer_id: UUID, payload: CustomerUpdate, current: CurrentUser = Depends(require_role("admin")), db: Session = Depends(get_db)) -> Customer:
    customer = db.scalar(select(Customer).where(Customer.id == customer_id, Customer.organization_id == current.organization.id).with_for_update())
    if customer is None:
        raise HTTPException(status_code=404, detail="CUSTOMER_NOT_FOUND")
    if customer.revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail="CUSTOMER_REVISION_CONFLICT")
    for key, value in payload.model_dump(exclude={"expected_revision"}).items():
        setattr(customer, key, value)
    customer.revision += 1
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="CUSTOMER_REFERENCE_CONFLICT") from error
    db.refresh(customer)
    return customer


@app.get("/api/v1/orders", response_model=list[OrderOut], tags=["orders"])
def list_orders(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[Order]:
    return list(db.scalars(select(Order).where(Order.organization_id == current.organization.id).order_by(Order.order_ref)))


@app.post("/api/v1/orders", response_model=OrderOut, status_code=201, tags=["orders"])
def create_order(payload: OrderCreate, current: CurrentUser = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)) -> Order:
    customer = db.scalar(select(Customer).where(Customer.id == payload.customer_id, Customer.organization_id == current.organization.id))
    if not customer:
        raise HTTPException(status_code=404, detail="CUSTOMER_NOT_FOUND")
    order = Order(organization_id=current.organization.id, **payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def order_detail(db: Session, order: Order) -> OrderDetailOut:
    lines = list(db.scalars(select(OrderLine).where(OrderLine.order_id == order.id, OrderLine.organization_id == order.organization_id).order_by(OrderLine.line_no)))
    return OrderDetailOut(id=order.id, order_ref=order.order_ref, customer_id=order.customer_id, status=order.status, revision=order.revision, lines=[OrderLineOut.model_validate(line) for line in lines])


@app.get("/api/v1/orders/{order_id}", response_model=OrderDetailOut, tags=["orders"])
def get_order(order_id: str, current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> OrderDetailOut:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.organization_id == current.organization.id))
    if not order:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
    return order_detail(db, order)


@app.put("/api/v1/orders/{order_id}/cart", response_model=OrderDetailOut, tags=["orders"])
def replace_cart(order_id: str, payload: CartReplace, current: CurrentUser = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)) -> OrderDetailOut:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.organization_id == current.organization.id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
    if order.revision != payload.expected_revision:
        raise HTTPException(status_code=409, detail="REVISION_CONFLICT")
    if order.status != "draft":
        raise HTTPException(status_code=409, detail="ORDER_NOT_EDITABLE")
    if len({line.packaging_unit_id for line in payload.lines}) != len(payload.lines):
        raise HTTPException(status_code=422, detail="DUPLICATE_PACKAGING_UNIT")
    old_lines = list(db.scalars(select(OrderLine).where(OrderLine.order_id == order.id, OrderLine.organization_id == current.organization.id).with_for_update()))
    if any(line.allocated_units for line in old_lines):
        raise HTTPException(status_code=409, detail="ORDER_ALREADY_ALLOCATED")
    new_lines: list[tuple[PackagingUnit, int]] = []
    for requested in payload.lines:
        unit = db.scalar(select(PackagingUnit).where(PackagingUnit.id == requested.packaging_unit_id, PackagingUnit.organization_id == current.organization.id))
        if not unit:
            raise HTTPException(status_code=404, detail="PACKAGING_UNIT_NOT_FOUND")
        new_lines.append((unit, requested.quantity_cartons * unit.units_per_package))
    for line in old_lines:
        db.delete(line)
    db.flush()
    for number, (unit, quantity_units) in enumerate(new_lines, 1):
        db.add(OrderLine(organization_id=current.organization.id, order_id=order.id, packaging_unit_id=unit.id, line_no=number, quantity_units=quantity_units, allocated_units=0))
    order.revision += 1
    db.commit()
    return order_detail(db, order)


@app.post("/api/v1/orders/{order_id}/lines", response_model=OrderLineOut, status_code=201, tags=["orders"])
def add_order_line(order_id: str, payload: OrderLineCreate, current: CurrentUser = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)) -> OrderLine:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.organization_id == current.organization.id))
    unit = db.scalar(select(PackagingUnit).where(PackagingUnit.id == payload.packaging_unit_id, PackagingUnit.organization_id == current.organization.id))
    if not order:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
    if not unit:
        raise HTTPException(status_code=404, detail="PACKAGING_UNIT_NOT_FOUND")
    line = OrderLine(organization_id=current.organization.id, order_id=order.id, **payload.model_dump())
    db.add(line)
    order.revision += 1
    db.commit()
    db.refresh(line)
    return line


@app.post("/api/v1/orders/{order_id}/shipments", response_model=ShipmentOut, status_code=201, tags=["shipments"])
def create_shipment(order_id: str, payload: ShipmentCreate, current: CurrentUser = Depends(require_role("sales", "admin")), db: Session = Depends(get_db)) -> ShipmentOut:
    order = db.scalar(select(Order).where(Order.id == order_id, Order.organization_id == current.organization.id).with_for_update())
    if not order:
        raise HTTPException(status_code=404, detail="ORDER_NOT_FOUND")
    if len({line.line_no for line in payload.lines}) != len(payload.lines):
        raise HTTPException(status_code=422, detail="DUPLICATE_ORDER_LINE")
    created_lines: list[OrderLine] = []
    for requested in payload.lines:
        line = db.scalar(select(OrderLine).where(OrderLine.order_id == order.id, OrderLine.line_no == requested.line_no, OrderLine.organization_id == current.organization.id).with_for_update())
        if not line:
            raise HTTPException(status_code=404, detail="ORDER_LINE_NOT_FOUND")
        if line.packaging_unit_id != requested.packaging_unit_id:
            raise HTTPException(status_code=409, detail="ORDER_LINE_PRODUCT_MISMATCH")
        if requested.quantity_units > line.quantity_units - line.allocated_units:
            raise HTTPException(status_code=409, detail="ORDER_QUANTITY_ALREADY_ALLOCATED")
        line.allocated_units += requested.quantity_units
        created_lines.append(OrderLine(id=line.id, packaging_unit_id=line.packaging_unit_id, line_no=line.line_no, quantity_units=requested.quantity_units, allocated_units=line.allocated_units))
    shipment = Shipment(organization_id=current.organization.id, order_id=order.id, shipment_ref=payload.shipment_ref)
    db.add(shipment)
    db.flush()
    for source in created_lines:
        db.add(ShipmentLine(organization_id=current.organization.id, shipment_id=shipment.id, order_line_id=source.id, quantity_units=source.quantity_units))
    db.commit()
    return ShipmentOut(id=shipment.id, order_id=shipment.order_id, shipment_ref=shipment.shipment_ref, status=shipment.status, revision=shipment.revision, lines=[OrderLineOut.model_validate(line) for line in created_lines])


@app.get("/api/v1/shipments", response_model=list[ShipmentOut], tags=["shipments"])
def list_shipments(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[ShipmentOut]:
    shipments = list(db.scalars(select(Shipment).where(Shipment.organization_id == current.organization.id).order_by(Shipment.shipment_ref)))
    result: list[ShipmentOut] = []
    for shipment in shipments:
        allocations = list(db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id, ShipmentLine.organization_id == current.organization.id)))
        lines: list[OrderLineOut] = []
        for allocation in allocations:
            source = db.scalar(select(OrderLine).where(OrderLine.id == allocation.order_line_id, OrderLine.organization_id == current.organization.id))
            if source:
                lines.append(OrderLineOut(id=source.id, packaging_unit_id=source.packaging_unit_id, line_no=source.line_no, quantity_units=allocation.quantity_units, allocated_units=source.allocated_units))
        result.append(ShipmentOut(id=shipment.id, order_id=shipment.order_id, shipment_ref=shipment.shipment_ref, status=shipment.status, revision=shipment.revision, lines=lines))
    return result


@app.get("/api/v1/admin/probe", response_model=MessageOut, tags=["admin"])
def admin_probe(_: CurrentUser = Depends(require_role("admin"))) -> MessageOut:
    return MessageOut(message="ADMIN_ACCESS_GRANTED")
