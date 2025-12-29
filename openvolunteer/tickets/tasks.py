import os
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.db.models import Count
from django.db.models import Q
from django.utils import timezone

from openvolunteer.events.models import EventStatus
from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import Person

from .models import Ticket
from .models import TicketBatch
from .models import TicketStatus
from .models import TicketTemplate
from .services import create_ticket
from .services import get_ticket_template_for_org


@shared_task(bind=True)
def delete_tickets(
    self,
    *,
    days_old: int = 30,
    statuses=None,
) -> int:
    """
    Delete completed tickets older than `days_old` days.

    Returns the number of deleted tickets.
    """

    if statuses is None:
        statuses = [
            TicketStatus.COMPLETED,
            TicketStatus.CANCELED,
        ]

    cutoff = timezone.now() - timedelta(days=days_old)

    qs = Ticket.objects.filter(
        status__in=[statuses],
        modified_at__lt=cutoff,
    )

    deleted_count, _ = qs.delete()
    return deleted_count


@shared_task(bind=True)
def delete_ticket_batches(self) -> int:
    """
    Delete ticket batches that:
    - Have zero tickets, OR
    - All associated tickets are completed
    """

    batches_qs = TicketBatch.objects.annotate(
        total_tickets=Count("tickets"),
        incomplete_tickets=Count(
            "tickets",
            filter=~Q(
                tickets__status__in=[TicketStatus.COMPLETED, TicketStatus.CANCELED],
            ),
        ),
    ).filter(
        Q(total_tickets=0) | Q(incomplete_tickets=0),
    )

    deleted_count, _ = batches_qs.delete()
    return deleted_count


@shared_task(bind=True)
def cancel_stale_tickets(
    self,
    *,
    statuses=None,
    days_stale: int = 10,
    new_status: str = TicketStatus.CANCELED,
) -> int:
    """
    Cancel tickets that have not been updated in X days and are in certain statuses.
    """

    if statuses is None:
        statuses = [
            TicketStatus.IN_PROGRESS,
            TicketStatus.BLOCKED,
        ]

    cutoff = timezone.now() - timedelta(days=days_stale)

    qs = Ticket.objects.filter(
        status__in=statuses,
        modified_at__lt=cutoff,
    )

    return qs.update(
        status=new_status,
    )


@shared_task(bind=True)
def cancel_tickets_for_canceled_events(
    self,
    *,
    days_recent: int = 3,
    new_status: str = TicketStatus.CANCELED,
) -> int:
    """
    Cancel tickets that belong to canceled events.
    """

    cutoff = timezone.now() - timedelta(days=days_recent)

    qs = Ticket.objects.filter(
        modified_at__lt=cutoff,
        event__event_status=EventStatus.CANCELED,
    )

    return qs.update(
        status=new_status,
    )


@shared_task(bind=True)
def create_tickets_for_people_with_tag(  # noqa: PLR0913
    self,
    *,
    template_name,
    tag_name: str,
    org_slugs: list[str] | None = None,
    batch_prefix: str | None = None,
    limit: int | None = None,
) -> int:
    """
    Create tickets for people that have a given tag.

    - If org_slugs is provided, only those orgs are processed
    - If org_slugs is None or empty, all orgs are processed
    """

    # Determine orgs to process
    if org_slugs:
        orgs = Organization.objects.filter(slug__in=org_slugs)
    else:
        orgs = Organization.objects.all()

    total_created = 0

    for org in orgs:
        # People with this tag in this org OR global tag
        people_qs = (
            Person.objects.filter(
                # Person must belong to the org
                org_links__org=org,
                org_links__is_active=True,
            )
            .filter(
                Q(
                    taggings__tag__name=tag_name,
                    taggings__tag__org=org,
                )
                | Q(
                    taggings__tag__name=tag_name,
                    taggings__tag__org__isnull=True,
                ),
            )
            .distinct()
        )

        template = get_ticket_template_for_org(template_name, org)

        if not template:
            msg = f"No TicketTemplate named '{template_name}' for org '{org}' or global"
            raise TicketTemplate.DoesNotExist(msg)

        if limit:
            people_qs = people_qs[:limit]

        name = (
            f"{batch_prefix if batch_prefix else template_name}-{os.urandom(2).hex()}"
        )
        reason = f"System generated batch for {template_name} on {timezone.now()}"
        batch = TicketBatch.objects.create(
            org=org,
            name=name,
            reason=reason,
            created_by=None,  # System
        )

        for person in people_qs:
            with transaction.atomic():
                create_ticket(
                    template=template,
                    org=org,
                    created_by=None,  # System
                    person=person,
                    batch=batch,
                )
                total_created += 1

        # Delete batch if no tickets created
        if not batch.tickets.exists():
            batch.delete()

    return total_created
