# people/permissions.py


def user_can_view_person(user, person) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    return person.org_links.filter(
        org__memberships__user=user,
        org__memberships__is_active=True,
        is_active=True,
    ).exists()


def user_can_edit_person(user, person) -> bool:
    if not user.is_authenticated:
        return False

    if user.is_staff or user.is_superuser:
        return True

    return person.org_links.filter(
        org__memberships__user=user,
        org__memberships__role__in=[
            "owner",
            "admin",
            "organizer",
        ],
        org__memberships__is_active=True,
        is_active=True,
    ).exists()


def user_can_create_person(user) -> bool:
    if not user.is_authenticated:
        return False

    # Superusers / staff can always create
    return user.is_staff or user.is_superuser
