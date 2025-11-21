from celery import Celery
from .config import settings

celery = Celery(__name__, broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery.conf.timezone = settings.TZ
celery.conf.beat_schedule = {
    "tick-schedules": {
        "task": "app.tasks.tick_schedules",
        "schedule": 60.0,
        "args": [],
    },
    # Ejemplo: escaneo diario (ajustable vía API en futuro)
    # "daily-demo-scan": {
    #     "task": "app.tasks.run_scheduled_scan",
    #     "schedule": 60.0 * 60 * 24,
    #     "args": ["example.com", ["amass","subfinder"]],
    # },
}
celery.conf.beat_schedule_filename = "/tmp/celerybeat-schedule"
celery.conf.update(imports=("app.tasks",))