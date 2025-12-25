from celery import Celery
from app.config import settings

celery_app = Celery(
    "arbitraggio",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scraping",
        "app.tasks.enhancement",
        "app.tasks.monitoring",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "scrape-subito-every-hour": {
        "task": "app.tasks.scraping.scrape_subito",
        "schedule": 3600.0,
        "args": (["nintendo switch", "playstation 5", "iphone"],),
    },
    "check-availability-every-2-hours": {
        "task": "app.tasks.monitoring.check_all_availability",
        "schedule": 7200.0,
    },
    "sync-ebay-orders-every-30-min": {
        "task": "app.tasks.monitoring.sync_ebay_orders",
        "schedule": 1800.0,
    },
}
