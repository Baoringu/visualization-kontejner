"""API boundary for the conservative pallet vertical slice."""

import hashlib
import json
from uuid import UUID, uuid5

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import CurrentUser, current_user, require_role
from app.models import (
    OrderLine,
    OutboxEvent,
    PackagingUnit,
    PalletType,
    PlanningRun,
    PlanVersion,
    Product,
    Shipment,
    ShipmentLine,
)
from app.schemas import (
    PackagingUnitOut,
    PackagingVerification,
    PalletTypeCreate,
    PalletTypeOut,
    PlanOut,
    PreflightOut,
    PreflightRequest,
    RunCreate,
    RunOut,
)

router = APIRouter(prefix="/api/v1", tags=["planning"])


def canonical_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@router.post("/packaging-units/{unit_id}/verify", response_model=PackagingUnitOut)
def verify_packaging(unit_id: UUID, payload: PackagingVerification, current: CurrentUser = Depends(require_role("admin")), db: Session = Depends(get_db)) -> PackagingUnit:
    unit = db.scalar(select(PackagingUnit).where(PackagingUnit.id == unit_id, PackagingUnit.organization_id == current.organization.id).with_for_update())
    if unit is None:
        raise HTTPException(404, "PACKAGING_UNIT_NOT_FOUND")
    if unit.revision != payload.expected_revision:
        raise HTTPException(409, "REVISION_CONFLICT")
    unit.evidence_ref = payload.evidence_ref
    unit.top_load_limit_g = payload.top_load_limit_g
    unit.allow_upright_90 = payload.allow_upright_90
    unit.is_verified = True
    unit.revision += 1
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/pallet-types", response_model=list[PalletTypeOut])
def list_pallet_types(current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[PalletType]:
    return list(db.scalars(select(PalletType).where(PalletType.organization_id == current.organization.id).order_by(PalletType.code)))


@router.post("/pallet-types", response_model=PalletTypeOut, status_code=201)
def create_pallet_type(payload: PalletTypeCreate, current: CurrentUser = Depends(require_role("admin")), db: Session = Depends(get_db)) -> PalletType:
    if payload.max_total_height_mm <= payload.deck_height_mm:
        raise HTTPException(422, "TOTAL_HEIGHT_NOT_ABOVE_DECK")
    pallet = PalletType(organization_id=current.organization.id, **payload.model_dump())
    db.add(pallet)
    db.commit()
    db.refresh(pallet)
    return pallet


def shipment_snapshot(db: Session, shipment: Shipment, pallet: PalletType) -> tuple[dict | None, PreflightOut]:
    blockers: list[str] = []
    lines = list(db.scalars(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment.id, ShipmentLine.organization_id == shipment.organization_id).order_by(ShipmentLine.id)))
    requested_units = sum(line.quantity_units for line in lines)
    if not lines:
        return None, PreflightOut(ready=False, blockers=["SHIPMENT_EMPTY"], requested_units=0, requested_cartons=None)
    cartons: list[dict] = []
    requested_cartons = 0
    for line in lines:
        order_line = db.scalar(select(OrderLine).where(OrderLine.id == line.order_line_id, OrderLine.organization_id == shipment.organization_id))
        unit = db.scalar(select(PackagingUnit).where(PackagingUnit.id == order_line.packaging_unit_id, PackagingUnit.organization_id == shipment.organization_id)) if order_line else None
        product = db.scalar(select(Product).where(Product.id == unit.product_id, Product.organization_id == shipment.organization_id)) if unit else None
        if not unit or not product:
            blockers.append("PACKAGING_UNIT_NOT_FOUND")
            continue
        if not unit.is_verified or not unit.evidence_ref:
            blockers.append("PACKAGING_NOT_VERIFIED")
        count, remainder = divmod(line.quantity_units, unit.units_per_package)
        if remainder:
            blockers.append("INCOMPLETE_CARTON_QUANTITY")
        requested_cartons += count
        cartons.append({"sku": product.sku, "name": product.name, "source_order_line_id": str(line.order_line_id), "evidence_ref": unit.evidence_ref, "length_mm": unit.length_mm, "width_mm": unit.width_mm, "height_mm": unit.height_mm, "mass_g": unit.mass_g, "top_load_limit_g": unit.top_load_limit_g, "allowed_orientations": ["upright_0", "upright_90"] if unit.allow_upright_90 else ["upright_0"], "instance_ids": [str(uuid5(shipment.id, f"{line.id}:{i}")) for i in range(count)]})
    if requested_cartons > 500:
        blockers.append("INSTANCE_LIMIT_EXCEEDED")
    if pallet.support_model != "solid_deck" or not pallet.evidence_ref:
        blockers.append("PALLET_SUPPORT_NOT_VERIFIED")
    if blockers:
        return None, PreflightOut(ready=False, blockers=sorted(set(blockers)), requested_units=requested_units, requested_cartons=requested_cartons)
    snapshot = {"schema_version": 2, "shipment_id": str(shipment.id), "shipment_revision": shipment.revision, "organization_id": str(shipment.organization_id), "quantity_units": requested_units, "cartons": cartons, "pallet": {"length_mm": pallet.length_mm, "width_mm": pallet.width_mm, "deck_height_mm": pallet.deck_height_mm, "max_total_height_mm": pallet.max_total_height_mm, "max_cargo_mass_g": pallet.max_cargo_mass_g, "tare_mass_g": pallet.tare_mass_g, "available_count": pallet.available_count, "support_model": pallet.support_model}, "evidence": {"packaging": [carton["evidence_ref"] for carton in cartons], "pallet": pallet.evidence_ref}}
    return snapshot, PreflightOut(ready=True, blockers=[], requested_units=requested_units, requested_cartons=requested_cartons)


@router.post("/shipments/{shipment_id}/preflight", response_model=PreflightOut)
def preflight(shipment_id: UUID, payload: PreflightRequest, current: CurrentUser = Depends(require_role("warehouse", "admin")), db: Session = Depends(get_db)) -> PreflightOut:
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id, Shipment.organization_id == current.organization.id))
    pallet = db.scalar(select(PalletType).where(PalletType.id == payload.pallet_type_id, PalletType.organization_id == current.organization.id))
    if not shipment or not pallet:
        raise HTTPException(404, "SHIPMENT_OR_PALLET_NOT_FOUND")
    return shipment_snapshot(db, shipment, pallet)[1]


def run_out(db: Session, run: PlanningRun) -> RunOut:
    plan = db.scalar(select(PlanVersion).where(PlanVersion.run_id == run.id, PlanVersion.organization_id == run.organization_id))
    return RunOut(id=run.id, shipment_id=run.shipment_id, status=run.status, termination_reason=run.termination_reason, error_code=run.error_code, plan_id=plan.id if plan else None)


@router.post("/shipments/{shipment_id}/runs", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
def create_run(shipment_id: UUID, payload: RunCreate, idempotency_key: str = Header(min_length=8, max_length=200), current: CurrentUser = Depends(require_role("warehouse", "admin")), db: Session = Depends(get_db)) -> RunOut:
    request_hash = canonical_hash(payload.model_dump(mode="json"))
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id, Shipment.organization_id == current.organization.id).with_for_update())
    if not shipment:
        raise HTTPException(404, "SHIPMENT_NOT_FOUND")
    old = db.scalar(select(PlanningRun).where(PlanningRun.organization_id == current.organization.id, PlanningRun.created_by_user_id == current.user.id, PlanningRun.shipment_id == shipment_id, PlanningRun.idempotency_key == idempotency_key))
    if old:
        if old.request_hash != request_hash:
            raise HTTPException(409, "IDEMPOTENCY_KEY_CONFLICT")
        return run_out(db, old)
    pallet = db.scalar(select(PalletType).where(PalletType.id == payload.pallet_type_id, PalletType.organization_id == current.organization.id))
    if not pallet:
        raise HTTPException(404, "PALLET_NOT_FOUND")
    if shipment.revision != payload.expected_shipment_revision:
        raise HTTPException(409, "REVISION_CONFLICT")
    snapshot, report = shipment_snapshot(db, shipment, pallet)
    if not report.ready or snapshot is None:
        raise HTTPException(422, "PREFLIGHT_BLOCKED:" + ",".join(report.blockers))
    snapshot["search"] = {"strategy": payload.strategy, "evaluation_budget": payload.evaluation_budget}
    run = PlanningRun(organization_id=current.organization.id, shipment_id=shipment.id, pallet_type_id=pallet.id, created_by_user_id=current.user.id, idempotency_key=idempotency_key, request_hash=request_hash, input_hash=canonical_hash(snapshot), input_snapshot=snapshot)
    db.add(run)
    db.flush()
    db.add(OutboxEvent(organization_id=current.organization.id, run_id=run.id))
    db.commit()
    return run_out(db, run)


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: UUID, current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> RunOut:
    run = db.scalar(select(PlanningRun).where(PlanningRun.id == run_id, PlanningRun.organization_id == current.organization.id))
    if not run:
        raise HTTPException(404, "RUN_NOT_FOUND")
    return run_out(db, run)


@router.get("/shipments/{shipment_id}/runs", response_model=list[RunOut])
def list_runs(shipment_id: UUID, current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> list[RunOut]:
    shipment = db.scalar(select(Shipment).where(Shipment.id == shipment_id, Shipment.organization_id == current.organization.id))
    if not shipment:
        raise HTTPException(404, "SHIPMENT_NOT_FOUND")
    runs = list(db.scalars(select(PlanningRun).where(PlanningRun.shipment_id == shipment_id, PlanningRun.organization_id == current.organization.id).order_by(PlanningRun.created_at.desc())))
    return [run_out(db, run) for run in runs]


@router.get("/plans/{plan_id}", response_model=PlanOut)
def get_plan(plan_id: UUID, current: CurrentUser = Depends(current_user), db: Session = Depends(get_db)) -> PlanVersion:
    plan = db.scalar(select(PlanVersion).where(PlanVersion.id == plan_id, PlanVersion.organization_id == current.organization.id))
    if not plan:
        raise HTTPException(404, "PLAN_NOT_FOUND")
    return plan
