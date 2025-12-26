from openvolunteer.orgs.permissions import user_can_edit_org
from openvolunteer.orgs.permissions import user_can_manage_people
from openvolunteer.orgs.permissions import user_can_view_org


def user_can_assign_people(user, event):
    return user_can_manage_people(
        user,
        event.org,
    ) or (user == event.owned_by)


def user_can_manage_events(user, event=None, org=None):
    if event is None and org is None:
        return False
    return user_can_manage_people(
        user,
        (event and event.org) or org,
    ) or (event and user == event.owned_by)


def user_can_view_events(user, event):
    return user_can_view_org(
        user,
        event.org,
    ) or (user == event.owned_by)


def user_can_edit_event_owner(user, event):
    return user_can_edit_org(user, event.org)
