from django.db import transaction
from django.utils import timezone

from openvolunteer.tickets.audit import log_ticket_event
from openvolunteer.tickets.models import TicketAuditEvent

from .handlers import ACTION_HANDLERS
from .models import TicketAction


class TicketActionService:
    @staticmethod
    @transaction.atomic
    def execute(action: TicketAction, user, is_system=True):  # noqa: FBT002
        ticket = action.ticket

        # Permission check
        if not is_system and user and ticket.assigned_to != user:
            msg = "Only the assigned user may perform this action"
            raise PermissionError(msg)
        if action.is_completed:
            msg = "Action already completed"
            raise ValueError(msg)
        handler = ACTION_HANDLERS[action.action_type]
        try:
            handler(ticket=ticket, action=action, user=user)
        except Exception as exc:
            log_ticket_event(
                ticket=ticket,
                event_type=TicketAuditEvent.ACTION_FAILED,
                message=f"Action '{action.label}' failed: {exc}",
                actor=user,
                success=False,
                metadata={
                    "action_type": action.action_type,
                    "error": str(exc),
                    "is_system": is_system,
                },
            )
            raise

        log_ticket_event(
            ticket=ticket,
            event_type=TicketAuditEvent.ACTION_RUN,
            message=f"Action '{action.label}' executed",
            actor=user,
            metadata={
                "action_type": action.action_type,
                "action_id": str(action.id),
                "is_system": is_system,
            },
        )
        # Update corresponding ticket status
        if (
            ticket
            and action.updates_ticket_status
            and len(action.updates_ticket_status) > 0
        ):
            old_status = ticket.status
            ticket.status = action.updates_ticket_status
            ticket.save(update_fields=["status"])
            log_ticket_event(
                ticket=ticket,
                event_type=TicketAuditEvent.STATUS_CHANGED,
                message=f"Status changed from '{old_status}' to '{ticket.status}'",
                actor=user,
                metadata={
                    "from": old_status,
                    "to": ticket.status,
                },
            )

        # Mark action complete
        action.is_completed = True
        action.completed_at = timezone.now()
        action.save(update_fields=["is_completed", "completed_at"])
