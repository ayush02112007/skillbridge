"""Celery application.

Tasks are thin wrappers around the same service functions the API calls, so
behaviour is identical whether work runs inline or on a worker. With
``CELERY_TASK_ALWAYS_EAGER`` (the default in development) everything executes
in-process, so a local run needs no broker.
"""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("celery")

celery_app = Celery(
    "skillbridge",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_max_tasks_per_child=200,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        "refresh-skill-demand": {
            "task": "skillbridge.refresh_skill_demand",
            # Nightly: keeps the taxonomy's demand signal in step with postings.
            "schedule": crontab(hour=2, minute=0),
        },
        "recompute-recommendations": {
            "task": "skillbridge.recompute_recommendations",
            "schedule": crontab(hour=3, minute=0),
        },
        "send-deadline-reminders": {
            "task": "skillbridge.send_deadline_reminders",
            "schedule": crontab(hour=8, minute=0),
        },
        "send-event-reminders": {
            "task": "skillbridge.send_event_reminders",
            "schedule": crontab(hour=9, minute=0),
        },
        "expire-stale-attempts": {
            "task": "skillbridge.expire_stale_attempts",
            "schedule": crontab(minute="*/30"),
        },
        "prune-expired-sessions": {
            "task": "skillbridge.prune_expired_sessions",
            "schedule": crontab(hour=4, minute=30),
        },
    },
)


def run_async(coroutine: Coroutine[Any, Any, Any]) -> Any:
    """Run an async service call from a synchronous Celery task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coroutine)
    # Already inside a loop (eager mode under the API): schedule and wait.
    return loop.run_until_complete(coroutine)  # pragma: no cover
