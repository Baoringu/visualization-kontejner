import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_foundation"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS pallet_building")
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("organizations", sa.Column("id", uuid, primary_key=True), sa.Column("name", sa.String(200), nullable=False), sa.Column("locale", sa.String(10), nullable=False, server_default="en"), sa.Column("timezone", sa.String(64), nullable=False, server_default="Europe/Prague"), schema="pallet_building")
    op.create_table("users", sa.Column("id", uuid, primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("display_name", sa.String(200), nullable=False), sa.Column("password_hash", sa.String(500), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), schema="pallet_building")
    op.create_table("memberships", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey("pallet_building.organizations.id"), nullable=False), sa.Column("user_id", uuid, sa.ForeignKey("pallet_building.users.id"), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.UniqueConstraint("organization_id", "user_id"), schema="pallet_building")
    op.create_table("sessions", sa.Column("id", uuid, primary_key=True), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("csrf_hash", sa.String(64), nullable=False), sa.Column("user_id", uuid, sa.ForeignKey("pallet_building.users.id"), nullable=False), sa.Column("organization_id", uuid, sa.ForeignKey("pallet_building.organizations.id"), nullable=False), sa.Column("role", sa.String(30), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema="pallet_building")


def downgrade() -> None:
    op.drop_table("sessions", schema="pallet_building")
    op.drop_table("memberships", schema="pallet_building")
    op.drop_table("users", schema="pallet_building")
    op.drop_table("organizations", schema="pallet_building")
