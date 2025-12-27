from zoneinfo import ZoneInfo

from django.db import transaction
from django.template import Context
from django.template import Template

from openvolunteer.events.models import ShiftAssignment
from openvolunteer.people.models import Person

from .models import Ticket
from .models import TicketBatch


def render_template(template_str: str, context: dict) -> str:
    return Template(template_str).render(Context(context)).strip()


# TODO: Move to another central file
TIMEZONES = {
    "utc": ("UTC", ZoneInfo("UTC")),
    "est": ("EST", ZoneInfo("America/New_York")),
    "cdt": ("CDT", ZoneInfo("America/Chicago")),
    "pdt": ("PDT", ZoneInfo("America/Los_Angeles")),
    "cet": ("CET", ZoneInfo("Europe/Paris")),
}


def format_event_times(dt):
    """
    Returns a dict-like object suitable for template access:

    starts_at_time
    starts_at_time.est
    starts_at_time.cdt
    starts_at_time.pdt
    starts_at_time.cet
    """

    def fmt(label, tz):
        localized = dt.astimezone(tz)
        return f"({localized.strftime('%-I:%M %p')} {label})"

    times = {}

    for key, (label, tz) in TIMEZONES.items():
        times[key] = fmt(label, tz)

    return times


# ruff: noqa: PLR0913
@transaction.atomic
def generate_tickets_for_event(
    *,
    event,
    created_by,
    ticket_templates=None,
    person_queryset=None,
    batch_name=None,
    reason="",
    include_default_shift=True,
):
    """
    Generate a TicketBatch + Tickets for an Event.

    - One ticket per (TicketTemplate by Person)
    - Persons are derived from shift assignments unless overridden
    - Tickets are NOT generated for unassigned people

    :param event: Event instance
    :param created_by: User creating the batch
    :param ticket_templates: Optional iterable of TicketTemplates
                             Defaults to event.template.ticket_templates
    :param person_queryset: Optional queryset of Person
                             Defaults to assigned people on event shifts
    :param batch_name: Optional override for batch name
    :param reason: Optional reason/audit note
    :param include_default_shift: Whether default shift assignments count
    """

    if not event.template:
        msg = "Event has no EventTemplate"
        raise ValueError(msg)

    if ticket_templates is None:
        ticket_templates = event.template.ticket_templates.filter(is_active=True)

    if not ticket_templates.exists():
        msg = "No active TicketTemplates attached to EventTemplate"
        raise ValueError(msg)

    # --------------------
    # Resolve people
    # --------------------

    assignments = ShiftAssignment.objects.filter(
        shift__event=event,
    )

    if not include_default_shift:
        assignments = assignments.exclude(shift__is_default=True)

    if person_queryset is not None:
        assignments = assignments.filter(person__in=person_queryset)

    people = assignments.values_list("person", flat=True).distinct()

    if not people:
        msg = "No assigned people found for event"
        raise ValueError(msg)

    # --------------------
    # Create batch
    # --------------------

    batch = TicketBatch.objects.create(
        org=event.org,
        event=event,
        name=batch_name or f"Generated tickets for {event.title}",
        reason=reason,
        created_by=created_by,
    )

    # --------------------
    # Generate tickets
    # --------------------

    tickets = []

    for tmpl in ticket_templates:
        if tmpl.max_tickets and tmpl.max_tickets < len(people):
            msg = f"TicketTemplate '{tmpl.name}' max_tickets exceeded"
            raise ValueError(msg)

        for person_id in people:
            context = {
                "event": event,
                "org": event.org,
                "starts_at_date": event.starts_at.strftime("%B %d, %Y"),
                "starts_at_time": format_event_times(event.starts_at),
                "assigned_user": None,
                "person": None,  # lazy load below
                "task_name": tmpl.name,
                "task_type": event.template.name,
            }

            # Lazy-load person only if template needs it
            person = Person.objects.get(id=person_id)
            context["person"] = person

            name = render_template(tmpl.ticket_name_template, context)
            description = render_template(
                tmpl.description_template,
                context,
            )

            ticket = Ticket.objects.create(
                org=event.org,
                batch=batch,
                event=event,
                person=person,
                name=name,
                description=description,
                priority=tmpl.default_priority,
                claimable=tmpl.claimable,
                reporter=created_by,
            )

            tickets.append(ticket)

    return batch, tickets
