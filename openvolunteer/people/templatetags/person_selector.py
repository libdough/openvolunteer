from django import template
from django.db.models import Q

from openvolunteer.events.models import Event
from openvolunteer.people.models import PersonTag

register = template.Library()


@register.inclusion_tag(
    "components/person_selector.html",
    takes_context=True,
)
def person_selector(context, **kwargs):
    """
    Self-sufficient person selector component.

    Accepted kwargs:
    - selected_people (required)
    - input_name
    - org_id
    - exclude_org_id
    - placeholder
    """

    org_id = kwargs.get("org_id")

    # ---- Bulk tags (global + org-scoped) ----
    bulk_tags = PersonTag.objects.all()
    if org_id:
        bulk_tags = bulk_tags.filter(
            Q(org__isnull=True) | Q(org_id=org_id),
        )

    bulk_tags = bulk_tags.order_by("name")

    # ---- Bulk events (scoped + limited) ----
    bulk_events = Event.objects.none()
    if org_id:
        bulk_events = Event.objects.filter(org_id=org_id).order_by("-starts_at")[:20]

    return {
        **context.flatten(),
        **kwargs,
        "bulk_tags": bulk_tags,
        "bulk_events": bulk_events,
    }
