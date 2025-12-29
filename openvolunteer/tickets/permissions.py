from openvolunteer.events.permissions import (
    user_can_assign_people as user_can_assign_people_event,
)
from openvolunteer.orgs.permissions import user_can_manage_members
from openvolunteer.orgs.permissions import user_can_participate
from openvolunteer.orgs.permissions import user_can_view_org

from .models import TicketStatus


def user_can_view_ticket(user, ticket):
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if ticket.assigned_to == user:
        return True

    if ticket.event and ticket.event.org:
        if user_can_view_org(user, ticket.event.org):
            return True

    return False


def user_can_assign_ticket(user, event=None):
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if event:
        return user_can_assign_people_event(
            user,
            event,
        )
    return False


def user_can_claim_ticket(user, ticket, event=None):
    if user.is_staff or user.is_superuser:
        return True

    if ticket.reporter == user:
        return True

    if event:
        if event.owned_by == user:
            return True

    if ticket.org:
        if not user_can_participate(user, ticket.org):
            return False
        if not ticket.claimable:
            # Only certain people can claim unclaimable tickets
            if user_can_manage_members(user, ticket.org):
                return True
    # Default to claimable tickets flag
    return ticket.claimable


def user_can_unclaim_ticket(user, ticket, event=None):
    if ticket.assigned_to is None:
        return False
    return user_can_claim_ticket(user, ticket, event)


def user_can_edit_ticket(user, ticket, event=None):
    if user.is_staff or user.is_superuser:
        return True

    if ticket.assigned_to == user:
        return True

    if ticket.reporter == user:
        return True

    if event:
        if event.owned_by == user:
            return True
        if user_can_manage_members(user, event.org):
            return True
    return False


def user_can_run_action(user, ticket, event):
    if ticket.status != TicketStatus.INPROGRESS:
        return False
    return user_can_edit_ticket(user, ticket, event)
