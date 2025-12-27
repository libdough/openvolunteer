#!/usr/bin/env python3
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import BadRequest
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.orgs.models import Membership
from openvolunteer.orgs.models import Organization
from openvolunteer.orgs.permissions import user_can_manage_people

from .filters import PERSON_FILTERS
from .forms import PersonCSVUploadForm
from .forms import PersonForm
from .models import Person
from .permissions import user_can_create_person
from .permissions import user_can_edit_person
from .permissions import user_can_view_person
from .services import handle_person_csv


@login_required
def person_list(request):
    # ================= BASE QUERYSET =================
    people = Person.objects.all()

    # Non-admin users only see people in their orgs
    if not (request.user.is_staff or request.user.is_superuser):
        org_ids = Membership.objects.filter(
            user=request.user,
            is_active=True,
        ).values_list("org_id", flat=True)

        people = people.filter(
            org_links__org_id__in=org_ids,
            org_links__is_active=True,
        )

    people = people.distinct().order_by("full_name")

    # ================= FILTERS =================
    people, filter_ctx = apply_filters(request, people, PERSON_FILTERS)

    # ================= PAGINATION =================
    pagination = paginate(request, people, per_page=20)

    return render(
        request,
        "people/person_list.html",
        {
            "can_edit": user_can_create_person(request.user),
            "people": pagination["page_obj"],
            **pagination,
            **filter_ctx,
        },
    )


@login_required
def person_detail(request, person_id):
    person = get_object_or_404(Person, id=person_id)

    if not user_can_view_person(request.user, person):
        raise Http404

    return render(
        request,
        "people/person_detail.html",
        {
            "person": person,
            "can_edit": user_can_edit_person(request.user, person),
        },
    )


@login_required
def person_form(request, person_id=None):
    """
    Create or edit a person.

    - If person_id is None → create
    - If person_id is set → edit
    """

    is_edit = person_id is not None
    person = None

    if is_edit:
        person = get_object_or_404(Person, id=person_id)

        if not user_can_edit_person(request.user, person):
            raise Http404

    if request.method == "POST":
        form = PersonForm(
            request.POST,
            instance=person,
            user=request.user,  # important for permission filtering
        )

        if form.is_valid():
            person = form.save()
            return redirect("people:person_detail", person_id=person.id)
    else:
        form = PersonForm(
            instance=person,
            user=request.user,
        )

    # --- Selected tags ---
    selected_tag_ids = set()
    selected_org_ids = set()

    if person:
        selected_tag_ids = set(
            person.taggings.values_list("tag_id", flat=True),
        )
        selected_org_ids = set(
            person.org_links.values_list("org_id", flat=True),
        )

    # --- Organizations user is allowed to manage ---
    organizations = [
        org
        for org in Organization.objects.all()
        if user_can_manage_people(request.user, org)
    ]

    return render(
        request,
        "people/person_form.html",
        {
            "form": form,
            "person": person,
            "is_edit": is_edit,
            "organizations": organizations,
            "selected_tag_ids": selected_tag_ids,
            "selected_org_ids": selected_org_ids,
        },
    )


@login_required
def person_upload_csv(request):
    if not user_can_create_person(request.user):
        raise Http404

    if request.method == "POST":
        form = PersonCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            created, skipped = handle_person_csv(
                request.user,
                request.FILES["csv_file"],
            )
            messages.success(
                request,
                f"Created {created} people. Skipped {skipped}.",
            )
            return redirect("people:person_list")
    else:
        form = PersonCSVUploadForm()

    return render(
        request,
        "people/person_upload.html",
        {"form": form},
    )


MIN_SEARCH_QUERY_LEN = 2
MAX_RESULTS = 10


@login_required
def person_search(request):
    """
    Search people by name / email / phone / discord / tags.
    Intended for org-admin / staff use.
    """
    user = request.user

    # ---- Permission gate ----
    if not (user.is_staff or user.is_superuser):
        if not Membership.objects.filter(
            user=user,
            is_active=True,
        ).exists():
            msg = "You do not have permission to search people."
            raise PermissionDenied(msg)

    q = request.GET.get("q", "").strip()
    org_id = request.GET.get("org_id")
    exclude_org_id = request.GET.get("exclude_org_id")

    if exclude_org_id == org_id:
        msg = f"Exclude and include org IDs match: {org_id}"
        raise BadRequest(msg)

    if len(q) < MIN_SEARCH_QUERY_LEN:
        return JsonResponse({"results": []})

    people = Person.objects.all()

    # ---- Visibility scoping ----
    if not (user.is_staff or user.is_superuser):
        org_ids = Membership.objects.filter(
            user=user,
            role__in=["owner", "admin", "organizer"],
            is_active=True,
        ).values_list("org_id", flat=True)

        people = people.filter(
            org_links__org_id__in=org_ids,
            org_links__is_active=True,
        )

    # ---- Optional include org scope ----
    if org_id:
        people = people.filter(
            org_links__org_id=org_id,
            org_links__is_active=True,
        )

    # ---- Optional exclude org scope ----
    if exclude_org_id:
        people = people.exclude(
            org_links__org_id=exclude_org_id,
            org_links__is_active=True,
        )

    people = (
        people.filter(
            Q(full_name__icontains=q)
            | Q(email__icontains=q)
            | Q(phone__icontains=q)
            | Q(discord__icontains=q)
            | Q(taggings__tag__name__icontains=q),
        )
        .distinct()
        .order_by("full_name")[:MAX_RESULTS]
    )

    people = people.prefetch_related("taggings__tag")

    return JsonResponse(
        {
            "results": [
                {
                    "id": str(person.id),
                    "name": person.full_name,
                    "email": person.email if user.is_staff else None,
                    "phone": person.phone if user.is_staff else None,
                    "discord": person.discord,
                    "tags": [
                        {
                            "name": t.tag.name,
                            "color": t.tag.color_hex,
                        }
                        for t in person.taggings.all()
                    ],
                }
                for person in people
            ],
        },
    )
