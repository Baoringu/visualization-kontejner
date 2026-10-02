import sqlalchemy as sa
from alembic import op

revision = "0004_customer_delivery"
down_revision = "0003_pallet_runs"


def upgrade() -> None:
    for name, length in (
        ("contact_name", 200),
        ("contact_email", 320),
        ("contact_phone", 50),
        ("ship_to_name", 200),
        ("ship_to_address_line1", 200),
        ("ship_to_address_line2", 200),
        ("ship_to_city", 120),
        ("ship_to_postal_code", 30),
        ("ship_to_country_code", 2),
        ("delivery_instructions", 1000),
    ):
        op.add_column("customers", sa.Column(name, sa.String(length)), schema="pallet_building")


def downgrade() -> None:
    for name in (
        "delivery_instructions", "ship_to_country_code", "ship_to_postal_code",
        "ship_to_city", "ship_to_address_line2", "ship_to_address_line1",
        "ship_to_name", "contact_phone", "contact_email", "contact_name",
    ):
        op.drop_column("customers", name, schema="pallet_building")
