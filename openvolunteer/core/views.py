from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from openvolunteer.orgs.models import Organization
from openvolunteer.tickets.queryset import get_filtered_tickets


@login_required
def home(request):
    ticket_ctx = get_filtered_tickets(claimed_by=request.user, limit=5)

    orgs = (
        Organization.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
        )
        .distinct()
        .annotate(
            people_count=Count(
                "people_links",
                distinct=True,
            ),
        )
        .order_by("name")
    )

    return render(
        request,
        "pages/home.html",
        {
            "user": request.user,
            "orgs": orgs,
            **ticket_ctx,
        },
    )
