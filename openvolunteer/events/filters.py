# events/filters.py

from .models import EventStatus
from .models import EventType

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
        "choices": EventType.choices,
        "lookup": "event_type",
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
