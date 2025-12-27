from .models import Organization


def orgs_for_user(user):
    return Organization.objects.filter(
        memberships__user=user,
        memberships__is_active=True,
    )
