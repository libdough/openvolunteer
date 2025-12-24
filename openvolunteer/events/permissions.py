from openvolunteer.orgs.permissions import user_can_manage_people


def user_can_assign_people(user, event):
    return user_can_manage_people(
        user,
        event.org,
    )
