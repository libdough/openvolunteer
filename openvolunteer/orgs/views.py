#!/usr/bin/env python3
from django.contrib.auth.decorators import login_required
from django.db.models import Case
from django.db.models import Count
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.events.models import Event
from openvolunteer.events.models import EventStatus
from openvolunteer.events.models import Shift
from openvolunteer.events.permissions import user_can_manage_events
from openvolunteer.people.models import PersonOrganization
from openvolunteer.users.models import User

from .filters import MEMBERSHIP_FILTERS
from .filters import PERSON_ORG_FILTERS
from .forms import AddMemberForm
from .forms import OrganizationForm
from .forms import UpdateMemberRoleForm
from .models import Membership
from .models import Organization
from .models import OrgRole
from .permissions import user_can_create_org
from .permissions import user_can_edit_org
from .permissions import user_can_manage_members
from .permissions import user_can_manage_people
from .permissions import user_can_view_org


@login_required
def org_list(request):
    if request.user.is_staff or request.user.is_superuser:
        orgs = Organization.objects.all()
    else:
        orgs = Organization.objects.filter(
            memberships__user=request.user,
            memberships__is_active=True,
        )

    orgs = (
        orgs.distinct()
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
        "orgs/org_list.html",
        {
            "orgs": orgs,
            "can_create_org": user_can_create_org(request.user),
        },
    )


@login_required
def org_detail(request, slug):
    org = (
        Organization.objects.annotate(
            people_count=Count(
                "people_links",
                filter=Q(people_links__is_active=True),
                distinct=True,
            ),
            member_count=Count(
                "memberships",
                filter=Q(memberships__is_active=True),
                distinct=True,
            ),
            event_count=Count(
                "events",
                filter=Q(events__event_status=EventStatus.SCHEDULED),
                distinct=True,
            ),
        )
        .filter(slug=slug)
        .first()
    )

    if not org:
        raise Http404

    if not user_can_view_org(request.user, org):
        raise Http404

    memberships = (
        Membership.objects.filter(org=org, is_active=True)
        .select_related("user")
        .order_by("role", "created_at")[:5]
    )

    people = (
        PersonOrganization.objects.filter(org=org, is_active=True)
        .select_related("person")
        .prefetch_related("person__taggings__tag")
        .order_by("person__full_name")[:5]
    )

    events = Event.objects.filter(org=org)

    if not user_can_manage_events(request.user, org=org):
        events = events.exclude(
            event_status__in=[
                EventStatus.DRAFT,
                EventStatus.FINISHED,
            ],
        )

    # Finished events always at bottom
    events = events.annotate(
        finished_sort=Case(
            When(event_status=EventStatus.FINISHED, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    ).order_by("finished_sort", "-starts_at")[:8]

    return render(
        request,
        "orgs/org_detail.html",
        {
            "org": org,
            "events": events,
            "memberships": memberships,
            "people": people,
            "can_edit_org": user_can_edit_org(request.user, org),
            "can_manage_members": user_can_manage_members(request.user, org),
            "can_manage_people": user_can_manage_people(request.user, org),
            "can_manage_events": user_can_manage_events(request.user, org=org),
        },
    )


@login_required
def org_create(request):
    if not user_can_create_org(request.user):
        raise Http404

    if request.method == "POST":
        form = OrganizationForm(request.POST)
        if form.is_valid():
            org = form.save()

            # Creator becomes OWNER
            Membership.objects.create(
                org=org,
                user=request.user,
                role=OrgRole.OWNER,
            )

            return redirect("orgs:org_detail", slug=org.slug)
    else:
        form = OrganizationForm()

    return render(
        request,
        "orgs/org_form.html",
        {
            "form": form,
            "org": None,
        },
    )


@login_required
def org_edit(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_edit_org(request.user, org):
        raise Http404

    if request.method == "POST":
        form = OrganizationForm(request.POST, instance=org)
        if form.is_valid():
            form.save()
            return redirect("orgs:org_detail", slug=org.slug)
    else:
        form = OrganizationForm(instance=org)

    return render(
        request,
        "orgs/org_form.html",
        {
            "org": org,
            "form": form,
        },
    )


@login_required
def org_members(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_manage_members(request.user, org):
        raise Http404

    members = org.memberships.select_related("user").order_by("role")

    if request.method == "POST":
        form = AddMemberForm(request.POST)
        if form.is_valid():
            user = User.objects.get(id=form.cleaned_data["user_id"])
            Membership.objects.update_or_create(
                org=org,
                user=user,
                defaults={
                    "role": form.cleaned_data["role"],
                    "is_active": True,
                },
            )
            return redirect("orgs:org_members", slug=slug)
        raise ValueError(form.errors)
    form = AddMemberForm()

    members, filter_ctx = apply_filters(request, members, MEMBERSHIP_FILTERS)
    pagination = paginate(request, members, per_page=20)

    role_choices = OrgRole.choices

    return render(
        request,
        "orgs/org_members.html",
        {
            "org": org,
            "members": pagination["page_obj"],
            **pagination,
            **filter_ctx,
            "role_choices": role_choices,
            "form": form,
        },
    )


@login_required
def org_member_update(request, slug, member_id):
    org = get_object_or_404(Organization, slug=slug)
    member = get_object_or_404(Membership, id=member_id, org=org)

    if not user_can_manage_members(request.user, org):
        raise Http404

    if request.method == "POST":
        form = UpdateMemberRoleForm(request.POST, instance=member)
        if form.is_valid():
            form.save()

    return redirect("orgs:org_members", slug=slug)


@login_required
def org_member_remove(request, slug, member_id):
    org = get_object_or_404(Organization, slug=slug)
    member = get_object_or_404(Membership, id=member_id, org=org)

    if not user_can_manage_members(request.user, org):
        raise Http404

    if request.method == "POST":
        member.delete()

    return redirect("orgs:org_members", slug=slug)


@login_required
def org_people(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_manage_people(request.user, org):
        raise Http404

    people_links = (
        org.people_links.select_related("person")
        .prefetch_related("person__taggings__tag")
        .order_by("person__full_name")
    )

    if request.method == "POST":
        # ---- ADD PEOPLE (new selector) ----
        if "add_people" in request.POST:
            person_ids = request.POST.getlist("people")

            if person_ids:
                PersonOrganization.objects.bulk_create(
                    [
                        PersonOrganization(
                            org=org,
                            person_id=pid,
                            is_active=True,
                        )
                        for pid in person_ids
                    ],
                    ignore_conflicts=True,
                )

            return redirect("orgs:org_people", slug=slug)

        # ---- REMOVE PERSON ----
        if "remove_person" in request.POST:
            link_id = request.POST.get("link_id")
            PersonOrganization.objects.filter(
                id=link_id,
                org=org,
            ).delete()
            return redirect("orgs:org_people", slug=slug)

    # ---- filters + pagination ----
    people_links, filter_ctx = apply_filters(
        request,
        people_links,
        PERSON_ORG_FILTERS,
    )

    pagination = paginate(request, people_links, per_page=20)

    return render(
        request,
        "orgs/org_people.html",
        {
            "org": org,
            "people_links": pagination["page_obj"],
            **pagination,
            **filter_ctx,
        },
    )


@login_required
def org_calendar_events(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_view_org(request.user, org):
        raise Http404

    # ---- EVENTS ----
    events_qs = Event.objects.filter(org=org)

    if not user_can_manage_events(request.user, org=org):
        events_qs = events_qs.filter(event_status=EventStatus.SCHEDULED)

    data = []

    data.extend(
        [
            {
                "id": f"events:{e.id}",
                "title": e.title,
                "start": e.starts_at.isoformat(),
                "end": e.ends_at.isoformat(),
                "url": reverse("events:event_detail", args=[e.id]),
                "editable": user_can_manage_events(request.user, event=e),
                "extendedProps": {
                    "type": "event",
                    "status": e.event_status,
                },
            }
            for e in events_qs
        ],
    )

    # ---- SHIFTS ----
    shifts = Shift.objects.filter(
        event__org=org,
        is_hidden=False,
    ).select_related("event")

    data.extend(
        [
            {
                "id": f"shifts:{s.id}",
                "title": f"{s.event.title}: {s.name}",
                "start": s.starts_at.isoformat(),
                "end": s.ends_at.isoformat(),
                "url": reverse("events:event_detail", args=[s.event_id]),
                "extendedProps": {
                    "type": "shift",
                    "status": s.event.event_status,
                },
            }
            for s in shifts
        ],
    )

    return JsonResponse(data, safe=False)


@login_required
def org_calendar(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_view_org(request.user, org):
        raise Http404

    return render(
        request,
        "orgs/org_calendar.html",
        {
            "org": org,
            "can_manage_events": user_can_manage_events(request.user, org=org),
        },
    )
