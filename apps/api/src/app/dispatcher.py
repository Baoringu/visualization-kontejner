"""Outbox dispatcher. Run as a separate process alongside API and Celery worker."""

import time
from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.models import OutboxEvent, PlanningRun
from app.tasks import process_run_task


def dispatch_once() -> int:
    delivered = 0
    with SessionLocal() as db:
        events = list(db.scalars(select(OutboxEvent).where(OutboxEvent.delivered_at.is_(None)).order_by(OutboxEvent.created_at).limit(20).with_for_update(skip_locked=True)))
        for event in events:
            process_run_task.delay(str(event.run_id))
            event.delivered_at = datetime.now(UTC)
            delivered += 1
        db.commit()
    with SessionLocal() as db:
        stale = list(db.scalars(select(PlanningRun).where(PlanningRun.status == "running", PlanningRun.lease_expires_at < datetime.now(UTC)).limit(20)))
        for run in stale:
            process_run_task.delay(str(run.id))
    return delivered


def main() -> None:
    while True:
        dispatch_once()
        time.sleep(2)


if __name__ == "__main__":
    main()
