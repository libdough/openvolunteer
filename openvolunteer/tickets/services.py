from zoneinfo import ZoneInfo

from django.db import transaction
from django.template import Context
from django.template import Template

from openvolunteer.events.models import ShiftAssignment

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

    """
    Generate a TicketBatch + Tickets for an Event.
    """

    if not event.template:
        msg = "Event has no EventTemplate"
        raise ValueError(msg)

    if ticket_templates is None:
        ticket_templates = event.template.ticket_templates.filter(is_active=True)

    if not ticket_templates.exists():
        msg = "No active TicketTemplates attached to EventTemplate"
        raise ValueError

    # --------------------
    # Resolve assignments / people
    # --------------------

    assignments_qs = ShiftAssignment.objects.filter(
        shift__event=event,
    ).select_related("shift", "person")

    if not include_default_shift:
        assignments_qs = assignments_qs.exclude(shift__is_default=True)

    if person_queryset is not None:
        assignments_qs = assignments_qs.filter(person__in=person_queryset)

    assignments = list(assignments_qs)

    if not assignments:
        msg = "No assigned people found for event"
        raise ValueError(msg)

    # Map person_id → assignment
    assignment_by_person_id = {a.person_id: a for a in assignments}

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
        if tmpl.max_tickets and tmpl.max_tickets < len(assignment_by_person_id):
            msg = f"TicketTemplate '{tmpl.name}' max_tickets exceeded"
            raise ValueError(msg)

        for assignment in assignment_by_person_id.values():
            person = assignment.person

            shift = assignment.shift if assignment else event.default_shift()

            context = {
                "event": event,
                "org": event.org,
                "starts_at_date": event.starts_at.strftime("%B %d, %Y"),
                "starts_at_time": format_event_times(event.starts_at),
                "shift": shift,
                "assigned_user": None,
                "person": person,
                "task_name": tmpl.name,
                "task_type": event.template.name,
            }

            name = render_template(tmpl.ticket_name_template, context)
            description = render_template(
                tmpl.description_template,
                context,
            )

            ticket = Ticket.objects.create(
                org=event.org,
                batch=batch,
                event=event,
                shift=shift,
                person=person,
                name=name,
                description=description,
                priority=tmpl.default_priority,
                claimable=tmpl.claimable,
                reporter=created_by,
            )

            create_actions_for_ticket(
                ticket=ticket,
                ticket_template=tmpl,
            )

            log_ticket_event(
                ticket=ticket,
                event_type=TicketAuditEvent.CREATED,
                message="Ticket created",
                actor=created_by,
                metadata={
                    "template": tmpl.name,
                    "batch": str(batch.id),
                },
            )

            tickets.append(ticket)

    return batch, tickets
