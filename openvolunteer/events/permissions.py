from openvolunteer.orgs.permissions import user_can_manage_people
from openvolunteer.orgs.permissions import user_can_view_org


def user_can_assign_people(user, event):
    return user_can_manage_people(
        user,
        event.org,
    )


def user_can_manage_events(user, event):
    return user_can_manage_people(
        user,
        event.org,
    )


def user_can_view_events(user, event):
    return user_can_view_org(
        user,
        event.org,
    )
