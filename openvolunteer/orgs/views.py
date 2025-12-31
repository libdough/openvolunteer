#!/usr/bin/env python3
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case
from django.db.models import Count
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Value
from django.db.models import When
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.events.models import Event
from openvolunteer.events.models import EventStatus
from openvolunteer.events.permissions import user_can_manage_events
from openvolunteer.people.models import PersonOrganization
from openvolunteer.tickets.models import TicketStatus
from openvolunteer.tickets.queryset import get_filtered_tickets

from .filters import MEMBERSHIP_FILTERS
from .filters import PERSON_ORG_FILTERS
from .forms import AddUserToOrgForm
from .forms import OrganizationForm
from .models import Membership
from .models import Organization
from .models import OrgRole
from .permissions import user_can_create_org
from .permissions import user_can_edit_org
from .permissions import user_can_manage_members
from .permissions import user_can_manage_people
from .permissions import user_can_set_role
from .permissions import user_can_view_org
from .queryset import orgs_for_user


@login_required
def org_list(request):
    if request.user.is_staff or request.user.is_superuser:
        orgs = Organization.objects.all()
    else:
        orgs = Organization.objects.filter(
            id__in=orgs_for_user(request.user),
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
        msg = "You do not have permission to view this org."
        raise PermissionDenied(msg)

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

    ticket_ctx = get_filtered_tickets(
        org=org,
        exclude_statuses=[
            TicketStatus.CANCELED,
            TicketStatus.COMPLETED,
        ]
        if not user_can_manage_events(request.user, org=org)
        else None,
        limit=5,
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
            **ticket_ctx,
        },
    )


@login_required
def org_create(request):
    if not user_can_create_org(request.user):
        msg = "You do not have permission to create new orgs."
        raise PermissionDenied(msg)

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
        msg = "You do not have permission to edit this org."
        raise PermissionDenied(msg)

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
        msg = "You do not have permission to manage members of this org."
        raise PermissionDenied(msg)

    members = org.memberships.select_related("user").order_by("-created_at")

    if request.method == "POST":
        form = AddUserToOrgForm(request.POST)
        if form.is_valid():
            # Verify that requesting user can change target's org role
            target_user = form.user
            new_role = form.cleaned_data["role"]
            existing = Membership.objects.filter(
                org=org,
                user=target_user,
            ).first()
            old_role = existing.role if existing else None
            if not user_can_set_role(
                request.user,
                org,
                new_role,
                old_role,
            ):
                msg = f"You cannot assign {new_role} to this user."
                raise PermissionDenied(msg)

            Membership.objects.update_or_create(
                org=org,
                user=target_user,
                defaults={
                    "role": new_role,
                    "is_active": True,
                },
            )

            return redirect("orgs:org_members", slug=slug)
    else:
        form = AddUserToOrgForm()

    members, filter_ctx = apply_filters(request, members, MEMBERSHIP_FILTERS)
    pagination = paginate(request, members, per_page=20)

    choices = [
        (value, label)
        for value, label in OrgRole.choices
        if user_can_set_role(request.user, org, value)
    ]
    return render(
        request,
        "orgs/org_members.html",
        {
            "org": org,
            "members": pagination["page_obj"],
            **pagination,
            **filter_ctx,
            "form": form,
            "role_choices": choices,
            "role_values": [value for value, _ in choices],
        },
    )


@login_required
def org_member_remove(request, slug, member_id):
    org = get_object_or_404(Organization, slug=slug)
    member = get_object_or_404(Membership, id=member_id, org=org)

    if not user_can_set_role(request.user, org, None, member.role):
        msg = "You can not remove this user"
        raise PermissionDenied(msg)

    if request.method == "POST":
        member.delete()

    return redirect("orgs:org_members", slug=slug)


@login_required
def org_people(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_manage_people(request.user, org):
        msg = "You do not have view people assigned to this org."
        raise PermissionDenied(msg)

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
def org_calendar(request, slug):
    org = get_object_or_404(Organization, slug=slug)

    if not user_can_view_org(request.user, org):
        msg = "You do not have permission to view this org's calendar."
        raise PermissionDenied(msg)

    return render(
        request,
        "orgs/org_calendar.html",
        {
            "org": org,
            "can_manage_events": user_can_manage_events(request.user, org=org),
        },
    )
