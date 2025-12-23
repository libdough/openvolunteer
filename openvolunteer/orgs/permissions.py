from .models import Membership
from .models import OrgRole


def user_is_org_member(user, org) -> bool:
    return Membership.objects.filter(
        user=user,
        org=org,
        is_active=True,
    ).exists()


def user_has_org_role(user, org, roles) -> bool:
    return Membership.objects.filter(
        user=user,
        org=org,
        role__in=roles,
        is_active=True,
    ).exists()


def user_can_view_org(user, org) -> bool:
    if user.is_staff or user.is_superuser:
        return True

    return user_is_org_member(user, org)


def user_can_edit_org_data(user, org) -> bool:
    if user.is_staff or user.is_superuser:
        return True

    return user_has_org_role(
        user,
        org,
        roles=[
            OrgRole.OWNER,
            OrgRole.ADMIN,
            OrgRole.ORGANIZER,
        ],
    )
