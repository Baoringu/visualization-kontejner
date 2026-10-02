"""Opt-in, idempotent synthetic catalog and order for local UX/planning checks.

All physical values are fictional fixtures, not load-bearing evidence.
"""

import argparse

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    Customer,
    Order,
    OrderLine,
    Organization,
    PackagingUnit,
    PalletType,
    Product,
    Shipment,
    ShipmentLine,
)

PRODUCTS = (
    ("DEMO-CLOTH", "DEMO ONLY · Folded textiles", "CARTON-12", 12, 400, 300, 180, 4000, 16000, True, 120),
    ("DEMO-GLASS", "DEMO ONLY · Fragile glassware", "UPRIGHT-1", 1, 300, 200, 250, 8000, 0, False, 6),
    ("DEMO-BOOK", "DEMO ONLY · Books", "CARTON-1", 1, 300, 200, 200, 10000, 20000, True, 5),
    ("DEMO-LAMP", "DEMO ONLY · Lamps", "UPRIGHT-1", 1, 500, 400, 350, 7000, 0, False, 3),
    ("DEMO-PARTS", "DEMO ONLY · Machine parts", "CARTON-1", 1, 600, 400, 220, 18000, 36000, True, 8),
)
EVIDENCE = "SYNTHETIC_DEMO_ONLY_NOT_PHYSICAL_EVIDENCE"


def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or insert synthetic demo fixtures; never deletes data")
    parser.add_argument("--execute", action="store_true", help="Explicitly insert missing demo rows")
    args = parser.parse_args()
    settings = get_settings()
    if settings.app_env != "development" or make_url(settings.database_url).database != "kontejner":
        raise SystemExit("Demo seed requires APP_ENV=development and database kontejner")
    with SessionLocal() as db:
        organizations = list(db.scalars(select(Organization).where(Organization.name == "Default Organization")))
        if len(organizations) != 1:
            raise SystemExit("Expected exactly one Default Organization; no data changed")
        org = organizations[0]
        print("Synthetic DEMO ONLY: 5 products/cartons, 2 customers, 1 solid-deck fixture, 1 order/shipment.")
        print("Existing data is preserved. Nothing is deleted or overwritten.")
        if not args.execute:
            print("Dry run. Use --execute to insert missing DEMO rows.")
            return
        unit_rows: list[tuple[PackagingUnit, int]] = []
        for sku, name, code, units, length, width, height, mass, top_load, rotate, quantity in PRODUCTS:
            product = db.scalar(select(Product).where(Product.organization_id == org.id, Product.sku == sku))
            if product is None:
                product = Product(organization_id=org.id, sku=sku, name=name)
                db.add(product)
                db.flush()
            package = db.scalar(select(PackagingUnit).where(PackagingUnit.organization_id == org.id, PackagingUnit.product_id == product.id, PackagingUnit.code == code))
            if package is None:
                package = PackagingUnit(organization_id=org.id, product_id=product.id, code=code, units_per_package=units, length_mm=length, width_mm=width, height_mm=height, mass_g=mass, is_verified=True, evidence_ref=EVIDENCE, top_load_limit_g=top_load, allow_upright_90=rotate)
                db.add(package)
                db.flush()
            unit_rows.append((package, quantity))
        for reference, name, city, line in (
            ("DEMO-CZ-1", "DEMO ONLY · Prague Retail", "Praha", "Demo Street 1"),
            ("DEMO-CZ-2", "DEMO ONLY · Brno Distribution", "Brno", "Example Avenue 20"),
        ):
            customer = db.scalar(select(Customer).where(Customer.organization_id == org.id, Customer.external_ref == reference))
            if customer is None:
                db.add(Customer(organization_id=org.id, external_ref=reference, name=name, ship_to_address_line1=line, ship_to_city=city, ship_to_postal_code="10000" if city == "Praha" else "60200", ship_to_country_code="CZ", delivery_instructions="Synthetic demo destination; do not dispatch."))
        pallet = db.scalar(select(PalletType).where(PalletType.organization_id == org.id, PalletType.code == "DEMO-SOLID-1200x800"))
        if pallet is None:
            db.add(PalletType(organization_id=org.id, code="DEMO-SOLID-1200x800", length_mm=1200, width_mm=800, deck_height_mm=150, max_total_height_mm=1250, max_cargo_mass_g=300000, tare_mass_g=30000, available_count=3, support_model="solid_deck", evidence_ref=EVIDENCE))
        customer = db.scalar(select(Customer).where(Customer.organization_id == org.id, Customer.external_ref == "DEMO-CZ-1"))
        if customer is None:
            db.flush()
            customer = db.scalar(select(Customer).where(Customer.organization_id == org.id, Customer.external_ref == "DEMO-CZ-1"))
        order = db.scalar(select(Order).where(Order.organization_id == org.id, Order.order_ref == "DEMO-MIXED-ORDER"))
        if order is None and customer is not None:
            order = Order(organization_id=org.id, customer_id=customer.id, order_ref="DEMO-MIXED-ORDER")
            db.add(order)
            db.flush()
            lines = []
            for number, (package, quantity) in enumerate(unit_rows, start=1):
                line = OrderLine(organization_id=org.id, order_id=order.id, packaging_unit_id=package.id, line_no=number, quantity_units=quantity, allocated_units=quantity)
                db.add(line)
                lines.append(line)
            db.flush()
            shipment = Shipment(organization_id=org.id, order_id=order.id, shipment_ref="DEMO-MIXED-SHIPMENT")
            db.add(shipment)
            db.flush()
            for line in lines:
                db.add(ShipmentLine(organization_id=org.id, shipment_id=shipment.id, order_line_id=line.id, quantity_units=line.quantity_units))
        db.commit()
    print("Demo seed complete. All dimensions/capacities are fictional and not approved for operation.")


if __name__ == "__main__":
    main()
