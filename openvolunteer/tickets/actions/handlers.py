from openvolunteer.events.models import ShiftAssignment
from openvolunteer.events.models import ShiftAssignmentStatus
from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import PersonTag
from openvolunteer.people.models import PersonTagging

from .models import TicketActionType


def _get_ticket_shift(ticket):
    """
    Return ticket.shift or event default shift.
    Default shift is guaranteed to exist.
    """
    return ticket.shift or ticket.event.default_shift()


def update_shift_status(*, ticket, action, user):
    shift = _get_ticket_shift(ticket)

    assignment = ShiftAssignment.objects.get(
        shift=shift,
        person=ticket.person,
    )

    new_status = action.config.get("status")
    assignment.status = new_status
    assignment.save(update_fields=["status"])


def upsert_shift_assignment(*, ticket, action, user):
    shift = _get_ticket_shift(ticket)

    ShiftAssignment.objects.update_or_create(
        shift=shift,
        person=ticket.person,
        defaults={
            "status": action.config.get(
                "status",
                ShiftAssignmentStatus.PENDING,
            ),
        },
    )


def upsert_tag(*, ticket, action, user):
    tag_name = action.config.get("tag", None)
    if not tag_name:
        return

    if not ticket.person:
        return

    org_slug = action.config.get("org_slug", None)
    org = Organization.objects.get(slug=org_slug)

    tag, _ = PersonTag.objects.get_or_create(
        org=org,
        name=tag_name,
    )

    PersonTagging.objects.get_or_create(
        person=ticket.person,
        tag=tag,
    )


def remove_tag(*, ticket, action, user):
    tag_name = action.config.get("tag", None)
    if not tag_name:
        return

    if not ticket.person:
        return

    org_slug = action.config.get("org_slug", None)
    org = Organization.objects.get(slug=org_slug)

    tag = PersonTag.objects.get(
        org=org,
        name=tag_name,
    )

    PersonTagging.objects.delete(
        person=ticket.person,
        tag=tag,
    )


def noop_action(*, ticket, action, user):
    """
    No-op action.

    Used for actions that only:
    - mark themselves completed
    - optionally update ticket status
    - produce an audit log
    """
    return


ACTION_HANDLERS = {
    TicketActionType.NOOP: noop_action,
    TicketActionType.UPDATE_SHIFT_STATUS: update_shift_status,
    TicketActionType.UPSERT_SHIFT_ASSIGNMENT: upsert_shift_assignment,
    TicketActionType.UPSERT_TAG: upsert_tag,
    TicketActionType.REMOVE_TAG: remove_tag,
}
