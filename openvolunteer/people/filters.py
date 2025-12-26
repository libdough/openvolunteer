from openvolunteer.orgs.models import Organization

from .models import PersonTag


def search_people(qs, request, value):
    """
    Search across multiple person identity fields.
    """
    return (
        qs.filter(
            full_name__icontains=value,
        )
        | qs.filter(
            email__icontains=value,
        )
        | qs.filter(
            discord__icontains=value,
        )
        | qs.filter(
            phone__icontains=value,
        )
    )


def filter_by_org(qs, request, value):
    return qs.filter(
        org_links__org_id=value,
        org_links__is_active=True,
    )


def filter_by_tag(qs, request, value):
    return qs.filter(
        taggings__tag_id=value,
    )


def filter_has_discord(qs, request, value):
    if value is True:
        return qs.exclude(discord__isnull=True).exclude(discord__exact="")
    if value is False:
        return qs.filter(discord__isnull=True) | qs.filter(discord__exact="")
    return qs


PERSON_FILTERS = [
    {
        "name": "q",
        "label": "Search",
        "type": "text",
        "filter": search_people,
    },
    {
        "name": "org",
        "label": "Organization",
        "type": "select",
        "filter": filter_by_org,
        "choices": lambda request: Organization.objects.filter(
            memberships__user=request.user,
        )
        .distinct()
        .values_list("id", "name"),
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
        "name": "has_discord",
        "label": "Has Discord",
        "type": "boolean",
        "filter": filter_has_discord,
    },
]
