# events/filters.py

from openvolunteer.orgs.queryset import orgs_for_user

from .models import EventStatus
from .models import EventTemplate

EVENT_FILTERS = [
    {
        "name": "q",
        "label": "Search",
        "type": "text",
        "lookup": "title__icontains",
    },
    {
        "name": "status",
        "label": "Status",
        "type": "select",
        "choices": EventStatus.choices,
        "lookup": "event_status",
    },
    {
        "name": "type",
        "label": "Type",
        "type": "select",
        "choices": lambda request: EventTemplate.objects.filter(
            org__in=orgs_for_user(request.user),
        ),
        "lookup": "template",
    },
    {
        "name": "owned",
        "label": "Owned by me",
        "type": "boolean",
        "filter": lambda qs, request, value: (
            qs.filter(owned_by=request.user) if value else qs
        ),
    },
]
