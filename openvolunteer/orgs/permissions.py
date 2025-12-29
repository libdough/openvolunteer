from .models import Membership
from .models import OrgRole


def _membership(user, org):
    return Membership.objects.filter(
        user=user,
        org=org,
        is_active=True,
    ).first()


def user_can_view_org(user, org):
    if user.is_staff or user.is_superuser:
        return True
    return _membership(user, org) is not None


def user_can_edit_org(user, org):
    if user.is_staff or user.is_superuser:
        return True
    m = _membership(user, org)
    return m and m.role in {OrgRole.OWNER, OrgRole.ADMIN}


def user_can_create_org(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or user.is_superuser


def user_can_manage_members(user, org) -> bool:
    if user.is_superuser:
        return True

    if not user.is_authenticated:
        return False

    m = _membership(user, org)
    return m and m.role in {OrgRole.OWNER, OrgRole.ADMIN}


def user_can_manage_people(user, org) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    m = _membership(user, org)
    return m and m.role in {OrgRole.OWNER, OrgRole.ADMIN, OrgRole.ORGANIZER}


# User has some level of edit participation
def user_can_participate(user, org) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    if not org:
        return False

    m = _membership(user, org)
    return m and m.role is not OrgRole.VIEWER
