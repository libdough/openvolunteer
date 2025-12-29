from datetime import timedelta

import pytest
from django.utils import timezone

from openvolunteer.events.models import Event
from openvolunteer.events.models import EventStatus
from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import Person
from openvolunteer.people.models import PersonOrganization
from openvolunteer.people.models import PersonTag
from openvolunteer.people.models import PersonTagging
from openvolunteer.tickets.models import Ticket
from openvolunteer.tickets.models import TicketBatch
from openvolunteer.tickets.models import TicketStatus
from openvolunteer.tickets.models import TicketTemplate
from openvolunteer.tickets.tasks import cancel_stale_tickets
from openvolunteer.tickets.tasks import cancel_tickets_for_canceled_events
from openvolunteer.tickets.tasks import create_tickets_for_people_with_tag
from openvolunteer.tickets.tasks import delete_ticket_batches
from openvolunteer.tickets.tasks import delete_tickets

# ruff: noqa: PLR2004


@pytest.mark.django_db
def test_delete_tickets_deletes_old_completed_and_canceled():
    old_time = timezone.now() - timedelta(days=40)
    recent_time = timezone.now() - timedelta(days=5)

    t1 = Ticket.objects.create(
        status=TicketStatus.COMPLETED,
        modified_at=old_time,
    )
    t2 = Ticket.objects.create(
        status=TicketStatus.CANCELED,
        modified_at=old_time,
    )
    t3 = Ticket.objects.create(
        status=TicketStatus.COMPLETED,
        modified_at=recent_time,
    )
    t4 = Ticket.objects.create(
        status=TicketStatus.IN_PROGRESS,
        modified_at=old_time,
    )

    deleted = delete_tickets(days_old=30)

    assert deleted == 2
    assert Ticket.objects.filter(id=t1.id).exists() is False
    assert Ticket.objects.filter(id=t2.id).exists() is False
    assert Ticket.objects.filter(id=t3.id).exists() is True
    assert Ticket.objects.filter(id=t4.id).exists() is True


@pytest.mark.django_db
def test_delete_ticket_batches():
    org = Organization.objects.create(name="Org", slug="org")

    empty_batch = TicketBatch.objects.create(
        org=org,
        name="empty",
        reason="test",
        created_by=None,
    )

    completed_batch = TicketBatch.objects.create(
        org=org,
        name="completed",
        reason="test",
        created_by=None,
    )
    Ticket.objects.create(
        batch=completed_batch,
        status=TicketStatus.COMPLETED,
    )

    active_batch = TicketBatch.objects.create(
        org=org,
        name="active",
        reason="test",
        created_by=None,
    )
    Ticket.objects.create(
        batch=active_batch,
        status=TicketStatus.IN_PROGRESS,
    )

    deleted = delete_ticket_batches()

    assert deleted == 2
    assert TicketBatch.objects.filter(id=empty_batch.id).exists() is False
    assert TicketBatch.objects.filter(id=completed_batch.id).exists() is False
    assert TicketBatch.objects.filter(id=active_batch.id).exists() is True


@pytest.mark.django_db
def test_cancel_stale_tickets():
    old_time = timezone.now() - timedelta(days=20)
    recent_time = timezone.now() - timedelta(days=2)

    t1 = Ticket.objects.create(
        status=TicketStatus.IN_PROGRESS,
        modified_at=old_time,
    )
    t2 = Ticket.objects.create(
        status=TicketStatus.BLOCKED,
        modified_at=old_time,
    )
    t3 = Ticket.objects.create(
        status=TicketStatus.IN_PROGRESS,
        modified_at=recent_time,
    )
    t4 = Ticket.objects.create(
        status=TicketStatus.COMPLETED,
        modified_at=old_time,
    )

    updated = cancel_stale_tickets(days_stale=10)

    assert updated == 2

    t1.refresh_from_db()
    t2.refresh_from_db()
    t3.refresh_from_db()
    t4.refresh_from_db()

    assert t1.status == TicketStatus.CANCELED
    assert t2.status == TicketStatus.CANCELED
    assert t3.status == TicketStatus.IN_PROGRESS
    assert t4.status == TicketStatus.COMPLETED


@pytest.mark.django_db
def test_cancel_tickets_for_canceled_events():
    org = Organization.objects.create(name="Org", slug="org")

    canceled_event = Event.objects.create(
        org=org,
        title="Canceled",
        event_status=EventStatus.CANCELED,
    )
    active_event = Event.objects.create(
        org=org,
        title="Active",
        event_status=EventStatus.SCHEDULED,
    )

    old_time = timezone.now() - timedelta(days=10)

    t1 = Ticket.objects.create(
        event=canceled_event,
        status=TicketStatus.IN_PROGRESS,
        modified_at=old_time,
    )
    t2 = Ticket.objects.create(
        event=active_event,
        status=TicketStatus.IN_PROGRESS,
        modified_at=old_time,
    )

    updated = cancel_tickets_for_canceled_events(days_recent=3)

    assert updated == 1

    t1.refresh_from_db()
    t2.refresh_from_db()

    assert t1.status == TicketStatus.CANCELED
    assert t2.status == TicketStatus.IN_PROGRESS


@pytest.mark.django_db
def test_create_tickets_for_people_with_tag_creates_and_cleans_batches():
    org = Organization.objects.create(name="Org", slug="org")

    # Create ticket for later use
    _ = TicketTemplate.objects.create(
        name="Intro",
        org=org,
    )

    person = Person.objects.create(full_name="Alice")
    PersonOrganization.objects.create(
        person=person,
        org=org,
        is_active=True,
    )

    tag = PersonTag.objects.create(
        name="unintroduced",
        org=None,  # global
    )

    PersonTagging.objects.create(
        person=person,
        tag=tag,
    )

    created = create_tickets_for_people_with_tag(
        template_name="Intro",
        tag_name="unintroduced",
        org_slugs=[org.slug],
    )

    assert created == 1
    assert Ticket.objects.count() == 1
    assert TicketBatch.objects.count() == 1
