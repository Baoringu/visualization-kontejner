import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Membership, Organization, User
from app.security import hash_password


def seed() -> None:
    parser = argparse.ArgumentParser(description="Explicit development seed")
    parser.add_argument("--password", required=True, help="Development password; never use this in production")
    args = parser.parse_args()
    with SessionLocal() as db:
        organization = db.scalar(select(Organization).where(Organization.name == "Default Organization"))
        if not organization:
            organization = Organization(name="Default Organization")
            db.add(organization)
            db.flush()
        user = db.scalar(select(User).where(User.email == "admin@palletbuilding.dev"))
        if not user:
            user = User(email="admin@palletbuilding.dev", display_name="Development Admin", password_hash=hash_password(args.password))
            db.add(user)
            db.flush()
        if not db.scalar(select(Membership).where(Membership.user_id == user.id, Membership.organization_id == organization.id)):
            db.add(Membership(user_id=user.id, organization_id=organization.id, role="admin"))
        db.commit()
    print("Seed complete for admin@palletbuilding.dev")


if __name__ == "__main__":
    seed()
