# people/permissions.py
from orgs.models import Membership

from .models import PersonOrganization


def user_can_view_person(user, person) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    user_org_ids = Membership.objects.filter(
        user=user,
        is_active=True,
    ).values_list("org_id", flat=True)

    return PersonOrganization.objects.filter(
        person=person,
        org_id__in=user_org_ids,
        is_active=True,
    ).exists()
