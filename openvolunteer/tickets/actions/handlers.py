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


def create_shift_assignment(*, ticket, action, user):
    shift = _get_ticket_shift(ticket)

    ShiftAssignment.objects.create(
        shift=shift,
        person=ticket.person,
        status=action.config.get(
            "status",
            ShiftAssignmentStatus.PENDING,
        ),
        assigned_by=user,
    )


ACTION_HANDLERS = {
    TicketActionType.UPDATE_SHIFT_STATUS: update_shift_status,
    TicketActionType.CREATE_SHIFT_ASSIGNMENT: create_shift_assignment,
}
