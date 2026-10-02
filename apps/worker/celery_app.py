from celery import Celery

from app.config import get_settings

celery_app = Celery("pallet_building", broker=get_settings().redis_url, backend=get_settings().redis_url)


@celery_app.task(name="pallet_building.foundation.noop")
def foundation_noop() -> str:
    """Connectivity smoke task; it does not claim to perform packing."""
    return "foundation_worker_ready"
