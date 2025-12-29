from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import QuerySet
from django.db.models import Value
from django.db.models import When
from django.template import Context
from django.template import Template

from openvolunteer.events.models import ShiftAssignment
from openvolunteer.people.models import Person

from .actions.models import TicketAction
from .audit import log_ticket_event
from .models import Ticket
from .models import TicketAuditEvent
from .models import TicketBatch
from .models import TicketTemplate


def render_template(template_str: str, context: dict) -> str:
    return Template(template_str).render(Context(context)).strip()


# TODO: Move to another central file
TIMEZONES = {
    "utc": ("UTC", ZoneInfo("UTC")),
    "est": ("EST", ZoneInfo("America/New_York")),
    "cdt": ("CDT", ZoneInfo("America/Chicago")),
    "mst": ("MT", ZoneInfo("America/Denver")),
    "pdt": ("PDT", ZoneInfo("America/Los_Angeles")),
    "cet": ("CET", ZoneInfo("Europe/Paris")),
}


def format_event_times(dt):
    """
    Returns a dict suitable for template access:

    starts_at.utc
    starts_at.cdt
    starts_at.date.utc
    starts_at.time.cdt
    """

    result = {
        "date": {},
        "time": {},
    }

    for key, (label, tz) in TIMEZONES.items():
        localized = dt.astimezone(tz)

        # Full datetime string
        result[key] = localized.strftime(f"%b %-d, %Y %-I:%M %p {label}")

        # Date-only
        result["date"][key] = localized.strftime("%b %-d, %Y")

        # Time-only
        result["time"][key] = localized.strftime("%-I:%M %p")

    return result


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


# ruff: noqa: PLR0913, PLR0912, C901
@transaction.atomic
def generate_tickets_for_event(
    *,
    event,
    created_by,
    ticket_templates=None,
    person_queryset=None,
    batch_name=None,
    reason="",
    shift=None,
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
    elif isinstance(ticket_templates, QuerySet):
        pass
    else:
        # list / tuple / iterable → coerce to queryset
        ticket_templates = TicketTemplate.objects.filter(
            id__in=[t.id for t in ticket_templates],
        )
    if not ticket_templates.exists():
        msg = "No active TicketTemplates attached to EventTemplate"
        raise ValueError(msg)

    # --------------------
    # Resolve assignments / people
    # --------------------
    if not shift:
        assignments_qs = ShiftAssignment.objects.filter(
            shift__event=event,
        ).select_related(
            "shift",
            "person",
        )

        if not include_default_shift:
            assignments_qs = assignments_qs.exclude(shift__is_default=True)
    else:
        assignments_qs = ShiftAssignment.objects.filter(shift=shift).select_related(
            "shift",
            "person",
        )

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
        shift=shift,
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
                org=event.org,
                event=event,
                person=assignment.person,
                shift=shift if shift else assignment.shift,
                batch=batch,
                created_by=created_by,
            )

            tickets.append(ticket)
    return batch, tickets


@transaction.atomic
def create_ticket(
    *,
    template,
    org,
    created_by,
    person=None,
    event=None,
    batch=None,
    shift=None,
):
    """
    Create a Ticket and enforce all invariants:
    - system on-create action
    - user actions
    - audit logging
    """

    # Deduplication
    if Ticket.objects.filter(
        template=template,
        org=org,
        person=person if person else None,
        event=event if event else None,
    ).exists():
        return None

    def safe_attr(obj, attr, default=None):
        return getattr(obj, attr, default) if obj is not None else default

    def safe_name(user):
        if user is None:
            return None
        return user.name or user.username

    context = {
        "org_name": org.name,
        # Event-related
        "event_title": safe_attr(event, "title"),
        "event_owner": safe_name(safe_attr(event, "owned_by")),
        "event_type": safe_attr(safe_attr(event, "template"), "name"),
        "event_starts_at": (
            format_event_times(event.starts_at) if event and event.starts_at else None
        ),
        "event_ends_at": (
            format_event_times(event.ends_at) if event and event.ends_at else None
        ),
        # Shift-related
        "shift_starts_at": (
            format_event_times(shift.starts_at) if shift and shift.starts_at else None
        ),
        "shift_ends_at": (
            format_event_times(shift.ends_at) if shift and shift.ends_at else None
        ),
        # People
        "person": None,
        # Ticket / task
        "task_name": safe_attr(template, "name"),
        "task_type": safe_attr(safe_attr(event, "template"), "name"),
        # Reporter
        "reporter_name": safe_name(created_by),
    }

    # Lazy-load person only if provided and needed
    if person is not None:
        if isinstance(person, Person):
            person_obj = person
        else:
            person_obj = Person.objects.get(id=person)
        context["person"] = person_obj

    name = render_template(template.ticket_name_template, context)
    description = render_template(template.description_template, context)

    ticket = Ticket.objects.create(
        name=name,
        description=description,
        org=org,
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


def get_ticket_template_for_org(name, org):
    return (
        TicketTemplate.objects.filter(name=name, org__in=[org, None])
        .order_by(
            Case(
                When(org=org, then=Value(0)),
                When(org__isnull=True, then=Value(1)),
                output_field=IntegerField(),
            ),
        )
        .first()
    )
