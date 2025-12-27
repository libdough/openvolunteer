#!/usr/bin/env python3
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
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
