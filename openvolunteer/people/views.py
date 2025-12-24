#!/usr/bin/env python3
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.pagination import paginate
from openvolunteer.orgs.models import Membership

from .forms import PersonForm
from .models import Person
from .permissions import user_can_create_person
from .permissions import user_can_edit_person
from .permissions import user_can_view_person
from .services import create_person


@login_required
def person_list(request):
    # Admins can see everyone
    if request.user.is_staff or request.user.is_superuser:
        people = Person.objects.all().order_by("full_name")
    else:
        org_ids = Membership.objects.filter(
            user=request.user,
            is_active=True,
        ).values_list("org_id", flat=True)

        people = (
            Person.objects.filter(
                org_links__org_id__in=org_ids,
                org_links__is_active=True,
            )
            .distinct()
            .order_by("full_name")
        )

    pagination = paginate(request, people, per_page=20)

    return render(
        request,
        "people/person_list.html",
        {
            "can_edit": user_can_create_person(request.user),
            "people": pagination["page_obj"],
            **pagination,
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
def person_create(request):
    if request.method == "POST":
        form = PersonForm(request.POST)
        if form.is_valid():
            person = create_person(data=form.cleaned_data)
            return redirect("people:person_detail", person_id=person.id)
    else:
        form = PersonForm()

    return render(
        request,
        "people/person_form.html",
        {
            "form": form,
        },
    )


@login_required
def person_edit(request, person_id):
    person = get_object_or_404(Person, id=person_id)

    if not user_can_edit_person(request.user, person):
        raise Http404

    if request.method == "POST":
        form = PersonForm(request.POST, instance=person)
        if form.is_valid():
            form.save()
            return redirect("people:person_detail", person_id=person.id)
    else:
        form = PersonForm(instance=person)

    return render(
        request,
        "people/person_form.html",
        {
            "form": form,
            "person": person,
            "is_edit": True,
        },
    )
