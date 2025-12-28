from openvolunteer.events.models import ShiftAssignment
from openvolunteer.events.models import ShiftAssignmentStatus

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
        status=action.config.get(
            "status",
            ShiftAssignmentStatus.PENDING,
        ),
        assigned_by=user,
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
}
