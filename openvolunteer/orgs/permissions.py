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


# Can this user assign some role to a user for some org
def user_can_set_role(user, org, new_role=None, old_role=None) -> bool:
    # To start, make sure they can manage members
    if not user_can_manage_members(user, org):
        return True

    m = _membership(user, org)

    # Do not update OWNER roles
    if old_role == OrgRole.OWNER:
        return False

    # Only owners can update admins
    if old_role == OrgRole.ADMIN and m.role != OrgRole.OWNER:
        return False

    # Org admins are limited in who they can add (none means remove)
    if m.role == OrgRole.ADMIN:
        return new_role in [OrgRole.VIEWER, OrgRole.VOLUNTEER, OrgRole.ORGANIZER, None]
    if m.role == OrgRole.OWNER:
        # Org owners can add anyone but owners
        return new_role != OrgRole.OWNER
    return False


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
