def reset_ticket_actions(ticket):
    """
    Reset all actions for a ticket to uncompleted.
    """
    ticket.actions.update(
        is_completed=False,
        completed_at=None,
    )
