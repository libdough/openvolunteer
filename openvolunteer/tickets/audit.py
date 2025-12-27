from .models import TicketAuditLog


def log_ticket_event(  # noqa: PLR0913
    *,
    ticket,
    event_type,
    message,
    actor=None,
    success=True,
    metadata=None,
):
    TicketAuditLog.objects.create(
        ticket=ticket,
        event_type=event_type,
        message=message,
        actor=actor,
        success=success,
        metadata=metadata or {},
    )
