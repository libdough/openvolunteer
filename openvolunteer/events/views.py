#!/usr/bin/env python3
import uuid

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.pagination import paginate
from openvolunteer.people.models import Person

from .models import Event
from .models import Shift
from .models import ShiftAssignment
from .permissions import user_can_assign_people
from .permissions import user_can_view_events


@login_required
def event_list(request):
    events_qs = (
        Event.objects.select_related("org")
        .prefetch_related("shifts")
        .order_by("starts_at")
    )

    pagination = paginate(request, events_qs, per_page=20)

    return render(
        request,
        "events/event_list.html",
        {
            "events": pagination["page_obj"],
            **pagination,
        },
    )


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects.select_related("org"),
        id=event_id,
    )

    if not user_can_view_events(request.user, event):
        raise HttpResponse(status=403)

    shifts_qs = event.shifts.order_by("starts_at")

    pagination = paginate(request, shifts_qs, per_page=20)

    return render(
        request,
        "events/event_detail.html",
        {
            "can_assign_people": user_can_assign_people(request.user, event),
            "event": event,
            "shifts": pagination["page_obj"],
            **pagination,
        },
    )


@login_required
def shift_assign_people(request, shift_id):
    shift = get_object_or_404(
        Shift.objects.select_related("event__org"),
        id=shift_id,
    )

    if not user_can_assign_people(request.user, shift.event):
        raise Http404

    # People already in org
    people_qs = Person.objects.filter(
        org_links__org=shift.event.org,
    ).distinct()

    assigned_ids = set(
        shift.assignments.values_list("person_id", flat=True),
    )

    if request.method == "POST":
        all_person_ids = request.POST.getlist("all_people")
        add_person_ids = request.POST.getlist("add_people")
        remove_person_ids = request.POST.getlist("remove_people")

        # diff-based update
        to_add = (set(all_person_ids) - assigned_ids) | set(add_person_ids)
        to_remove = (assigned_ids - set(map(uuid.UUID, all_person_ids))) | set(
            remove_person_ids,
        )

        ShiftAssignment.objects.filter(
            shift=shift,
            person_id__in=to_remove,
        ).delete()

        ShiftAssignment.objects.bulk_create(
            [
                ShiftAssignment(
                    shift=shift,
                    person_id=pid,
                    assigned_by=request.user,
                )
                for pid in to_add
            ],
            update_conflicts=True,
            unique_fields=["shift", "person"],
            update_fields=["assigned_by"],
        )

        return redirect("events:event_detail", shift.event.id)

    return render(
        request,
        "events/shift_assign.html",
        {
            "shift": shift,
            "people": people_qs,
            "assigned_ids": assigned_ids,
        },
    )
