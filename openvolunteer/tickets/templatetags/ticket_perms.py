from django import template

from openvolunteer.tickets.permissions import user_can_claim_ticket

register = template.Library()


@register.simple_tag
def can_claim_ticket(user, ticket):
    """
    Usage:
      {% can_assign_ticket request.user ticket as can_assign %}
    """
    return user_can_claim_ticket(user, ticket, event=ticket.event)
