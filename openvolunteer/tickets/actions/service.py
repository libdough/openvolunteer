from django.db import transaction
from django.utils import timezone

from .handlers import ACTION_HANDLERS
from .models import TicketAction


class TicketActionService:
    @staticmethod
    @transaction.atomic
    def execute(action: TicketAction, user):
        ticket = action.ticket

        # Permission check
        if ticket.assigned_to != user:
            msg = "Only the assigned user may perform this action"
            raise PermissionError(msg)

        if action.is_completed:
            msg = "Action already completed"
            raise ValueError(msg)

        handler = ACTION_HANDLERS[action.action_type]
        handler(ticket=ticket, action=action, user=user)

        # ✅ THIS IS WHERE updates_ticket_status LIVES
        if action.updates_ticket_status and len(action.updates_ticket_status) > 0:
            ticket.status = action.updates_ticket_status
            ticket.save(update_fields=["status"])

        # Mark action complete
        action.is_completed = True
        action.completed_at = timezone.now()
        action.save(update_fields=["is_completed", "completed_at"])
