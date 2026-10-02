import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_pallet_runs"
down_revision = "0002_catalog_orders"


def upgrade() -> None:
    schema = "pallet_building"
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("packaging_units", sa.Column("evidence_ref", sa.String(500)), schema=schema)
    op.add_column("packaging_units", sa.Column("top_load_limit_g", sa.Integer()), schema=schema)
    op.add_column("packaging_units", sa.Column("allow_upright_90", sa.Boolean(), nullable=False, server_default=sa.false()), schema=schema)
    op.create_table("pallet_types", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("code", sa.String(100), nullable=False), sa.Column("length_mm", sa.Integer(), nullable=False), sa.Column("width_mm", sa.Integer(), nullable=False), sa.Column("deck_height_mm", sa.Integer(), nullable=False), sa.Column("max_total_height_mm", sa.Integer(), nullable=False), sa.Column("max_cargo_mass_g", sa.Integer(), nullable=False), sa.Column("tare_mass_g", sa.Integer(), nullable=False), sa.Column("available_count", sa.Integer(), nullable=False), sa.Column("support_model", sa.String(50), nullable=False), sa.Column("evidence_ref", sa.String(500), nullable=False), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("organization_id", "code"), schema=schema)
    op.create_table("planning_runs", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("shipment_id", uuid, sa.ForeignKey(f"{schema}.shipments.id"), nullable=False), sa.Column("pallet_type_id", uuid, sa.ForeignKey(f"{schema}.pallet_types.id"), nullable=False), sa.Column("created_by_user_id", uuid, sa.ForeignKey(f"{schema}.users.id"), nullable=False), sa.Column("idempotency_key", sa.String(200), nullable=False), sa.Column("request_hash", sa.String(64), nullable=False), sa.Column("input_hash", sa.String(64), nullable=False), sa.Column("input_snapshot", postgresql.JSONB(), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="queued"), sa.Column("termination_reason", sa.String(50)), sa.Column("error_code", sa.String(100)), sa.Column("fence", sa.Integer(), nullable=False, server_default="0"), sa.Column("lease_expires_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("organization_id", "created_by_user_id", "shipment_id", "idempotency_key"), schema=schema)
    op.create_table("plan_versions", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("run_id", uuid, sa.ForeignKey(f"{schema}.planning_runs.id"), nullable=False, unique=True), sa.Column("shipment_id", uuid, sa.ForeignKey(f"{schema}.shipments.id"), nullable=False), sa.Column("input_hash", sa.String(64), nullable=False), sa.Column("layout_hash", sa.String(64), nullable=False), sa.Column("layout", postgresql.JSONB(), nullable=False), sa.Column("validation_status", sa.String(30), nullable=False), sa.Column("validator_version", sa.String(30), nullable=False), sa.Column("instruction_version", sa.String(30), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema=schema)
    op.create_table("outbox_events", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("run_id", uuid, sa.ForeignKey(f"{schema}.planning_runs.id"), nullable=False, unique=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("delivered_at", sa.DateTime(timezone=True)), schema=schema)


def downgrade() -> None:
    for table in ("outbox_events", "plan_versions", "planning_runs", "pallet_types"):
        op.drop_table(table, schema="pallet_building")
    for column in ("allow_upright_90", "top_load_limit_g", "evidence_ref"):
        op.drop_column("packaging_units", column, schema="pallet_building")
