"""Celery execution of immutable pallet snapshots with database fencing."""

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

from celery import Celery
from pallet_building_packer import (
    Carton,
    PackRequest,
    Pallet,
    make_instructions,
    pack,
    validate_instruction_sequence,
    validate_result,
)
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import PlanningRun, PlanVersion
from app.planning import canonical_hash

celery_app = Celery("pallet_building", broker=get_settings().redis_url)
celery_app.conf.update(task_acks_late=True, worker_prefetch_multiplier=1, task_serializer="json", accept_content=["json"], task_time_limit=30)


def _request_from_snapshot(snapshot: dict) -> PackRequest:
    groups = snapshot["cartons"] if snapshot["schema_version"] >= 2 else [{**snapshot["carton"], "instance_ids": snapshot["instance_ids"]}]
    cartons = tuple(Carton(instance_id=identifier, sku=group["sku"], length_mm=group["length_mm"], width_mm=group["width_mm"], height_mm=group["height_mm"], mass_g=group["mass_g"], top_load_limit_g=group["top_load_limit_g"], allowed_orientations=tuple(group["allowed_orientations"])) for group in groups for identifier in group["instance_ids"])
    pallet_data = snapshot["pallet"]
    pallet = Pallet(length_mm=pallet_data["length_mm"], width_mm=pallet_data["width_mm"], deck_height_mm=pallet_data["deck_height_mm"], max_total_height_mm=pallet_data["max_total_height_mm"], max_cargo_mass_g=pallet_data["max_cargo_mass_g"], available_count=pallet_data["available_count"], support_model=pallet_data["support_model"])
    options = snapshot.get("search", {})
    return PackRequest(cartons, pallet, strategy=options.get("strategy", "quick"), evaluation_budget=options.get("evaluation_budget", 250_000))


def process_run(run_id: UUID) -> str:
    with SessionLocal() as db:
        run = db.scalar(select(PlanningRun).where(PlanningRun.id == run_id).with_for_update())
        if run is None:
            return "missing"
        now = datetime.now(UTC)
        if run.status in {"succeeded", "failed", "cancelled"}:
            return run.status
        if run.status == "running" and run.lease_expires_at and run.lease_expires_at > now:
            return "already_running"
        run.fence += 1
        fence = run.fence
        run.status = "running"
        run.lease_expires_at = now + timedelta(seconds=30)
        snapshot = run.input_snapshot
        db.commit()
    try:
        request = _request_from_snapshot(snapshot)
        result = pack(request)
        findings = validate_result(request, result)
        if findings:
            raise ValueError("VALIDATION_FAILED:" + ",".join(findings))
        placements = [asdict(item) for item in result.placed]
        unplaced = [asdict(item) for item in result.unplaced]
        instructions = list(make_instructions(result))
        sequence_findings = validate_instruction_sequence(request, result, instructions)
        if sequence_findings:
            raise ValueError("INSTRUCTION_VALIDATION_FAILED:" + ",".join(sequence_findings))
        used_pallets = len({item.pallet_index for item in result.placed})
        placed_ids = {item.instance_id for item in result.placed}
        cargo_mass_g = sum(carton.mass_g for carton in request.cartons if carton.instance_id in placed_ids)
        cargo_height_mm = max((item.z_mm + item.height_mm for item in result.placed), default=0)
        layout = {"scope": "pallet_only", "placed": placements, "unplaced": unplaced, "instructions": instructions, "requested_instances": len(request.cartons), "placed_instances": len(placements), "unplaced_instances": len(unplaced), "pallet_count": used_pallets, "pallet": snapshot["pallet"], "carton": snapshot.get("carton"), "cartons": snapshot.get("cartons", []), "cargo_mass_g": cargo_mass_g, "loaded_mass_g": cargo_mass_g + used_pallets * snapshot["pallet"]["tare_mass_g"], "cargo_height_mm": cargo_height_mm, "loaded_height_mm": cargo_height_mm + snapshot["pallet"]["deck_height_mm"] if used_pallets else 0, "model_checks": {"geometry": "passed", "column_vertical_load": "passed", "instruction_prefix": "passed", "transport_dynamics": "not_evaluated"}, "search": {"termination_reason": result.termination_reason, "evaluations_completed": result.evaluations_completed, "candidates_completed": result.candidates_completed, "strategy": request.strategy}}
        layout_hash = canonical_hash(layout)
        with SessionLocal() as db:
            run = db.scalar(select(PlanningRun).where(PlanningRun.id == run_id).with_for_update())
            if run is None or run.fence != fence or run.status != "running":
                return "fenced_out"
            existing = db.scalar(select(PlanVersion).where(PlanVersion.run_id == run_id))
            if existing is None:
                db.add(PlanVersion(organization_id=run.organization_id, run_id=run.id, shipment_id=run.shipment_id, input_hash=run.input_hash, layout_hash=layout_hash, layout=layout, validation_status="passed", validator_version="exact_support_validator_v2", instruction_version="exact_support_sequence_v2"))
            run.status = "succeeded"
            run.termination_reason = result.termination_reason
            run.lease_expires_at = None
            db.commit()
        return "succeeded"
    except Exception:
        with SessionLocal() as db:
            run = db.scalar(select(PlanningRun).where(PlanningRun.id == run_id).with_for_update())
            if run and run.fence == fence and run.status == "running":
                run.status = "failed"
                run.error_code = "ENGINE_OR_VALIDATION_ERROR"
                run.lease_expires_at = None
                db.commit()
        raise


@celery_app.task(name="pallet_building.process_run")
def process_run_task(run_id: str) -> str:
    return process_run(UUID(run_id))
