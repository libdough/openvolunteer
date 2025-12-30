from django.db.models import Q

from openvolunteer.events.models import EventTemplate
from openvolunteer.orgs.queryset import orgs_for_user

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

    if value == "others":
        return qs.filter(assigned_to__isnull=False).exclude(assigned_to=request.user)

    return qs


def filter_exclude_statuses(qs, request, value):
    """
    Exclude orgs filter:
    - value: comma-separated list of statuses (e.g. "open,closed")
    """
    if not value:
        return qs

    if isinstance(value, str):
        statuses = [v for v in value.split(",") if v.strip()]
    else:
        # Defensively ignore bad value
        return qs

    if not statuses:
        return qs

    return qs.exclude(status__in=statuses)


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
        "name": "exclude_statuses",
        "label": "",
        "type": "hidden",
        "filter": filter_exclude_statuses,
    },
    {
        "name": "priority",
        "label": "Priority",
        "type": "select",
        "choices": [(i, f"P{i}") for i in range(6)],
        "lookup": "priority",
    },
    {
        "name": "org",
        "label": "",
        "type": "hidden",
        "lookup": "org",
    },
    {
        "name": "person",
        "label": "",
        "type": "hidden",
        "lookup": "person",
    },
    {
        "name": "event",
        "label": "",
        "type": "hidden",
        "lookup": "event",
    },
    {
        "name": "event_type",
        "label": "Event Type",
        "type": "select",
        "choices": lambda request: (
            EventTemplate.objects.filter(
                Q(org__memberships__user=request.user) | Q(org__isnull=True),
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
            ("others", "Assigned to others"),
            ("unassigned", "Unassigned"),
        ],
        "filter": filter_assignment,
    },
]
