from django.db.models import Q

from openvolunteer.events.models import EventTemplate
from openvolunteer.orgs.queryset import orgs_for_user

from .models import Ticket
from .models import TicketBatch
from .models import TicketStatus


def search_tickets(qs, request, value):
    if not value:
        return qs

    return qs.filter(
        Q(name__icontains=value)
        | Q(batch__name__icontains=value)
        | Q(description__icontains=value),
    )


def filter_assignment(qs, request, value):
    """
    Assignment filter:
    - "me"         -> assigned to current user
    - "unassigned" -> not assigned
    - None         -> no filtering
    """
    if value == "me":
        return qs.filter(assigned_to=request.user)

    if value == "unassigned":
        return qs.filter(assigned_to__isnull=True)

    return qs


TICKET_FILTERS = [
    {
        "name": "q",
        "label": "Search",
        "type": "text",
        "filter": search_tickets,
    },
    {
        "name": "status",
        "label": "Status",
        "type": "select",
        "choices": TicketStatus.choices,
        "lookup": "status",
    },
    {
        "name": "priority",
        "label": "Priority",
        "type": "select",
        "choices": [(i, f"P{i}") for i in range(6)],
        "lookup": "priority",
    },
    {
        "name": "event",
        "label": "Event",
        "type": "select",
        # Scoped by org via queryset passed into filter system
        "choices": lambda request: (
            Ticket.objects.filter(org__in=orgs_for_user(request.user))
            .exclude(event__isnull=True)
            .values_list("event__id", "event__title")
            .distinct()
            .order_by("event__title")
        ),
        "lookup": "event",
    },
    {
        "name": "event_type",
        "label": "Event Template",
        "type": "select",
        "choices": lambda request: (
            EventTemplate.objects.filter(
                org__memberships__user=request.user,
            ).distinct()
        ),
        "lookup": "event__template",
    },
    {
        "name": "batch",
        "label": "Ticket Batch",
        "type": "select",
        "choices": lambda request: (
            TicketBatch.objects.filter(org__in=orgs_for_user(request.user))
        ),
        "lookup": "batch",
    },
    {
        "name": "assignment",
        "label": "Assignment",
        "type": "select",
        "choices": [
            ("me", "Assigned to me"),
            ("unassigned", "Unassigned"),
        ],
        "filter": filter_assignment,
    },
]
