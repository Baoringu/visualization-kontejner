from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "pallet_building"}
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Prague", nullable=False)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "pallet_building"}
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.users.id"))
    role: Mapped[str] = mapped_column(String(30), nullable=False)


class SessionRecord(Base):
    __tablename__ = "sessions"
    __table_args__ = {"schema": "pallet_building"}
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    csrf_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.users.id"))
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"))
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "sku"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PackagingUnit(Base):
    __tablename__ = "packaging_units"
    __table_args__ = (UniqueConstraint("organization_id", "product_id", "code"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.products.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    units_per_package: Mapped[int] = mapped_column(Integer, nullable=False)
    length_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    width_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    height_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    mass_g: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_ref: Mapped[str | None] = mapped_column(String(500))
    top_load_limit_g: Mapped[int | None] = mapped_column(Integer)
    allow_upright_90: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("organization_id", "external_ref"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(200))
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    ship_to_name: Mapped[str | None] = mapped_column(String(200))
    ship_to_address_line1: Mapped[str | None] = mapped_column(String(200))
    ship_to_address_line2: Mapped[str | None] = mapped_column(String(200))
    ship_to_city: Mapped[str | None] = mapped_column(String(120))
    ship_to_postal_code: Mapped[str | None] = mapped_column(String(30))
    ship_to_country_code: Mapped[str | None] = mapped_column(String(2))
    delivery_instructions: Mapped[str | None] = mapped_column(String(1000))
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("organization_id", "order_ref"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    customer_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.customers.id"), nullable=False)
    order_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("order_id", "line_no"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.orders.id"), nullable=False)
    packaging_unit_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.packaging_units.id"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_units: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (UniqueConstraint("organization_id", "shipment_ref"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.orders.id"), nullable=False)
    shipment_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ShipmentLine(Base):
    __tablename__ = "shipment_lines"
    __table_args__ = (UniqueConstraint("shipment_id", "order_line_id"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    shipment_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.shipments.id"), nullable=False)
    order_line_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.order_lines.id"), nullable=False)
    quantity_units: Mapped[int] = mapped_column(Integer, nullable=False)


class PalletType(Base):
    __tablename__ = "pallet_types"
    __table_args__ = (UniqueConstraint("organization_id", "code"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    length_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    width_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    deck_height_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    max_total_height_mm: Mapped[int] = mapped_column(Integer, nullable=False)
    max_cargo_mass_g: Mapped[int] = mapped_column(Integer, nullable=False)
    tare_mass_g: Mapped[int] = mapped_column(Integer, nullable=False)
    available_count: Mapped[int] = mapped_column(Integer, nullable=False)
    support_model: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class PlanningRun(Base):
    __tablename__ = "planning_runs"
    __table_args__ = (UniqueConstraint("organization_id", "created_by_user_id", "shipment_id", "idempotency_key"), {"schema": "pallet_building"})
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    shipment_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.shipments.id"), nullable=False)
    pallet_type_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.pallet_types.id"), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.users.id"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    termination_reason: Mapped[str | None] = mapped_column(String(50))
    error_code: Mapped[str | None] = mapped_column(String(100))
    fence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PlanVersion(Base):
    __tablename__ = "plan_versions"
    __table_args__ = {"schema": "pallet_building"}
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.planning_runs.id"), nullable=False, unique=True)
    shipment_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.shipments.id"), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    layout_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    layout: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(30), nullable=False)
    validator_version: Mapped[str] = mapped_column(String(30), nullable=False)
    instruction_version: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = {"schema": "pallet_building"}
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.organizations.id"), nullable=False)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("pallet_building.planning_runs.id"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
