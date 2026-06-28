from celery import Celery
from celery.schedules import crontab
from kombu import Queue, Exchange
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "c_tp_grader",
    broker  = settings.REDIS_URL,
    backend = settings.REDIS_URL,
    include = ["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer    = "json",
    result_serializer  = "json",
    accept_content     = ["json"],
    timezone           = "UTC",
    enable_utc         = True,
    result_expires     = 60 * 60 * 24,
    task_acks_late                = True,
    task_reject_on_worker_lost    = True,
    worker_prefetch_multiplier    = 1,
    task_track_started            = True,
    task_soft_time_limit          = 300,
    task_time_limit               = 360,
    task_default_queue            = "default",
    task_queues = (
        Queue("default",     Exchange("default"),     routing_key="default"),
        Queue("evaluation",  Exchange("evaluation"),  routing_key="evaluation"),
        Queue("generation",  Exchange("generation"),  routing_key="generation"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
    ),
    task_routes = {
        "app.workers.tasks.evaluate_submission_task":     {"queue": "evaluation"},
        "app.workers.tasks.generate_tests_task":          {"queue": "generation"},
        "app.workers.tasks.bulk_reevaluate_task":         {"queue": "evaluation"},
        "app.workers.tasks.evaluate_expired_assignments": {"queue": "maintenance"},
        "app.workers.tasks.cleanup_old_tasks":            {"queue": "maintenance"},
    },
    beat_schedule = {
        # Check every 2 minutes for assignments whose deadline just passed
        "check-expired-assignments": {
            "task":     "app.workers.tasks.evaluate_expired_assignments",
            "schedule": 120,   # every 2 minutes
        },
        # Daily cleanup at 3 AM UTC
        "cleanup-old-task-results": {
            "task":     "app.workers.tasks.cleanup_old_tasks",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)


def get_celery() -> Celery:
    return celery_app