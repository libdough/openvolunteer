import json

from django_celery_beat.models import CrontabSchedule
from django_celery_beat.models import PeriodicTask


def install_default_tasks():
    midnight, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="5",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="UTC",
    )

    finish_elapsed_events = PeriodicTask.objects.get_or_create(
        name="Mark elapsed events as finished",
        defaults={
            "task": "openvolunteer.events.tasks.mark_events_as_finished",
            "crontab": midnight,
            "kwargs": json.dumps(
                {
                    "buffer_minutes": 00,
                },
            ),
            "enabled": True,
            "description": "Cancel old tasks that have not been modified in 30 days",
        },
    )

    clean_event_objects = PeriodicTask.objects.get_or_create(
        name="Cleanup Event Objects",
        defaults={
            "task": "openvolunteer.events.tasks.clean_event_objects",
            "crontab": midnight,
            "enabled": True,
            "description": (
                "Cleans up some shifts and assignments objects. "
                "This task will update shifts to start and end within event times. "
                "It also removes shift assignments set to inactive."
            ),
        },
    )

    cleanup_old_draft_events = PeriodicTask.objects.get_or_create(
        name="Cleanup Old Event Drafts",
        defaults={
            "task": "openvolunteer.events.tasks.cleanup_old_draft_events",
            "crontab": midnight,
            "kwargs": json.dumps(
                {
                    "days": 30,
                },
            ),
            "enabled": True,
            "description": ("Removes draft events older than 30 days."),
        },
    )

    return {
        "finish_elapsed_events": finish_elapsed_events,
        "clean_event_objects": clean_event_objects,
        "cleanup_old_draft_events": cleanup_old_draft_events,
    }
