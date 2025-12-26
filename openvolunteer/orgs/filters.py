from django.db.models import Q

from openvolunteer.people.models import PersonTag

from .models import OrgRole


def search_memberships(qs, request, value):
    """
    Search by user name or email.
    """
    return qs.filter(
        Q(user__name__icontains=value) | Q(user__email__icontains=value),
    )


def filter_by_role(qs, request, value):
    return qs.filter(role=value)


def filter_is_active(qs, request, value):
    """
    Tri-state boolean:
    - True  -> active only
    - False -> inactive only
    """
    if value is True:
        return qs.filter(is_active=True)
    if value is False:
        return qs.filter(is_active=False)
    return qs


MEMBERSHIP_FILTERS = [
    {
        "name": "q",
        "label": "Search User",
        "type": "text",
        "filter": search_memberships,
    },
    {
        "name": "role",
        "label": "Role",
        "type": "select",
        "filter": filter_by_role,
        "choices": OrgRole.choices,
    },
    {
        "name": "is_active",
        "label": "Active",
        "type": "boolean",
        "filter": filter_is_active,
    },
]


def search_people_orgs(qs, request, value):
    """
    Search across person identity fields.
    Mirrors PERSON_FILTERS search behavior.
    """
    return qs.filter(
        Q(person__full_name__icontains=value)
        | Q(person__email__icontains=value)
        | Q(person__discord__icontains=value)
        | Q(person__phone__icontains=value),
    )


def filter_by_tag(qs, request, value):
    """
    Filter PersonOrganization rows by person tag.
    """
    return qs.filter(
        person__taggings__tag_id=value,
    )


def filter_has_discord(qs, request, value):
    if value is True:
        return qs.exclude(person__discord__isnull=True).exclude(
            person__discord__exact="",
        )
    if value is False:
        return qs.filter(person__discord__isnull=True) | qs.filter(
            person__discord__exact="",
        )
    return qs


PERSON_ORG_FILTERS = [
    {
        "name": "q",
        "label": "Search Person",
        "type": "text",
        "filter": search_people_orgs,
    },
    {
        "name": "tag",
        "label": "Tag",
        "type": "select",
        "filter": filter_by_tag,
        "choices": lambda request: PersonTag.objects.filter(
            org__in=request.user.memberships.values("org"),
        )
        | PersonTag.objects.filter(org__isnull=True),
    },
    {
        "name": "is_active",
        "label": "Active",
        "type": "boolean",
        "filter": filter_is_active,
    },
    {
        "name": "has_discord",
        "label": "Has Discord",
        "type": "boolean",
        "filter": filter_has_discord,
    },
]
