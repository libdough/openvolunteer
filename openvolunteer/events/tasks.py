from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Event
from .models import EventStatus
from .models import ShiftAssignment


@shared_task(bind=True)
def mark_events_as_finished(self, buffer_minutes: int = 0):
    """
    Mark scheduled events as finished once their end time has elapsed.

    :param buffer_minutes: Optional grace period (in minutes) after ends_at
                           before marking an event as finished.
    :return: number of events updated
    """
    now = timezone.now()
    cutoff = now - timedelta(minutes=buffer_minutes)

    qs = Event.objects.filter(
        event_status=EventStatus.SCHEDULED,
        ends_at__lte=cutoff,
    )

    # Use update() for efficiency and idempotency
    with transaction.atomic():
        return qs.update(event_status=EventStatus.FINISHED)


@shared_task()
def clean_event_objects():
    updated_count = 0

    # Ensures every event has exactly one default shift.
    # Keeps default shift times aligned with the event
    for event in Event.objects.all():
        shift = event.default_shift()
        changed = False

        if shift.starts_at < event.starts_at:
            shift.starts_at = event.starts_at
            changed = True

        if shift.ends_at > event.ends_at:
            shift.ends_at = event.ends_at
            changed = True

        if changed:
            shift.save()
            updated_count += 1

    # Deletes inactive shift assignments from the DB
    if ShiftAssignment.objects.filter(
        person__org_links__is_active=False,
    ).delete():
        updated_count += 1

    return updated_count


@shared_task()
def cleanup_old_draft_events(days: int = 30):
    """
    Marks draft events as finished if they have not been modified
    within the given number of days.

    Uses modified_at (not created_at) to avoid expiring actively edited drafts.
    """
    cutoff = timezone.now() - timedelta(days=days)

    return Event.objects.filter(
        event_status=EventStatus.DRAFT,
        modified_at__lte=cutoff,
    ).update(event_status=EventStatus.CANCELED)
