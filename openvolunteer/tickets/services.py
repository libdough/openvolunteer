from zoneinfo import ZoneInfo

from django.db import transaction
from django.template import Context
from django.template import Template

from openvolunteer.events.models import ShiftAssignment
from openvolunteer.people.models import Person

from .actions.models import TicketAction
from .audit import log_ticket_event
from .models import Ticket
from .models import TicketAuditEvent
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


def create_actions_for_ticket(*, ticket, ticket_template):
    """
    Instantiate TicketActions from TicketActionTemplates.
    """
    action_templates = ticket_template.action_templates.filter(is_active=True)

    actions = [
        TicketAction(
            ticket=ticket,
            template=action_tmpl,
            run_when=action_tmpl.run_when,
            label=action_tmpl.label,
            action_type=action_tmpl.action_type,
            button_color=action_tmpl.button_color,
            updates_ticket_status=action_tmpl.updates_ticket_status,
            config=action_tmpl.config,
        )
        for action_tmpl in action_templates
    ]

    TicketAction.objects.bulk_create(actions)


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
    # Resolve assignments / people
    # --------------------
    assignments_qs = ShiftAssignment.objects.filter(shift__event=event).select_related(
        "shift",
        "person",
    )

    if not include_default_shift:
        assignments_qs = assignments_qs.exclude(shift__is_default=True)

    if person_queryset is not None:
        assignments_qs = assignments_qs.filter(person__in=person_queryset)

    assignments = list(assignments_qs)

    if not assignments:
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
        if tmpl.max_tickets and tmpl.max_tickets < len(assignments):
            msg = f"TicketTemplate '{tmpl.name}' max_tickets exceeded"
            raise ValueError(
                msg,
            )

        for assignment in assignments:
            ticket = create_ticket(
                template=tmpl,
                event=event,
                person=assignment.person,
                shift=assignment.shift,
                batch=batch,
                created_by=created_by,
            )

            tickets.append(ticket)
    return batch, tickets


@transaction.atomic
def create_ticket(
    *,
    template,
    event,
    person,
    created_by,
    batch=None,
    shift=None,
):
    """
    Create a Ticket and enforce all invariants:
    - system on-create action
    - user actions
    - audit logging
    """

    context = {
        "event": event,
        "org": event.org,
        "starts_at": event.starts_at,
        "assigned_user": None,
        "person": None,  # lazy load below
        "task_name": template.name,
        "task_type": event.template.name,
    }

    # Lazy-load person only if template needs it
    person = Person.objects.get(id=person.id)
    context["person"] = person

    name = render_template(template.ticket_name_template, context)
    message = render_template(template.description_template, context)

    ticket = Ticket.objects.create(
        name=name,
        description=message,
        org=event.org,
        event=event,
        person=person,
        batch=batch,
        shift=shift,
        reporter=created_by,
        priority=template.default_priority,
        claimable=template.claimable,
    )

    # Create user-visible actions
    create_actions_for_ticket(
        ticket=ticket,
        ticket_template=template,
    )

    log_ticket_event(
        ticket=ticket,
        event_type=TicketAuditEvent.CREATED,
        message="Ticket created",
        actor=created_by,
        metadata={
            "template": template.name,
            "batch": str(batch.id),
        },
    )

    return ticket
