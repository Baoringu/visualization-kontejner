import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_catalog_orders"
down_revision = "0001_foundation"


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    schema = "pallet_building"
    op.create_table("products", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("sku", sa.String(100), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.UniqueConstraint("organization_id", "sku"), schema=schema)
    op.create_table("packaging_units", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("product_id", uuid, sa.ForeignKey(f"{schema}.products.id"), nullable=False), sa.Column("code", sa.String(100), nullable=False), sa.Column("units_per_package", sa.Integer(), nullable=False), sa.Column("length_mm", sa.Integer(), nullable=False), sa.Column("width_mm", sa.Integer(), nullable=False), sa.Column("height_mm", sa.Integer(), nullable=False), sa.Column("mass_g", sa.Integer(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()), sa.UniqueConstraint("organization_id", "product_id", "code"), schema=schema)
    op.create_table("customers", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("external_ref", sa.String(100), nullable=False), sa.Column("name", sa.String(200), nullable=False), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("organization_id", "external_ref"), schema=schema)
    op.create_table("orders", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("customer_id", uuid, sa.ForeignKey(f"{schema}.customers.id"), nullable=False), sa.Column("order_ref", sa.String(100), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("organization_id", "order_ref"), schema=schema)
    op.create_table("order_lines", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("order_id", uuid, sa.ForeignKey(f"{schema}.orders.id"), nullable=False), sa.Column("packaging_unit_id", uuid, sa.ForeignKey(f"{schema}.packaging_units.id"), nullable=False), sa.Column("line_no", sa.Integer(), nullable=False), sa.Column("quantity_units", sa.Integer(), nullable=False), sa.Column("allocated_units", sa.Integer(), nullable=False, server_default="0"), sa.UniqueConstraint("order_id", "line_no"), schema=schema)
    op.create_table("shipments", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("order_id", uuid, sa.ForeignKey(f"{schema}.orders.id"), nullable=False), sa.Column("shipment_ref", sa.String(100), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="draft"), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.UniqueConstraint("organization_id", "shipment_ref"), schema=schema)
    op.create_table("shipment_lines", sa.Column("id", uuid, primary_key=True), sa.Column("organization_id", uuid, sa.ForeignKey(f"{schema}.organizations.id"), nullable=False), sa.Column("shipment_id", uuid, sa.ForeignKey(f"{schema}.shipments.id"), nullable=False), sa.Column("order_line_id", uuid, sa.ForeignKey(f"{schema}.order_lines.id"), nullable=False), sa.Column("quantity_units", sa.Integer(), nullable=False), sa.UniqueConstraint("shipment_id", "order_line_id"), schema=schema)


def downgrade() -> None:
    for table in ("shipment_lines", "shipments", "order_lines", "orders", "customers", "packaging_units", "products"):
        op.drop_table(table, schema="pallet_building")
