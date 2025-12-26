#!/usr/bin/env python3
import uuid

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.forms import modelformset_factory
from django.http import Http404
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_POST

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import Person
from openvolunteer.users.models import User

from .filters import EVENT_FILTERS
from .forms import EventForm
from .forms import ShiftForm
from .models import Event
from .models import Shift
from .models import ShiftAssignment
from .permissions import user_can_assign_people
from .permissions import user_can_edit_event_owner
from .permissions import user_can_manage_events


@login_required
def event_list(request):
    qs = Event.objects.select_related("org").order_by("starts_at")

    qs, filter_ctx = apply_filters(request, qs, EVENT_FILTERS)
    pagination = paginate(request, qs, per_page=20)

    return render(
        request,
        "events/event_list.html",
        {
            "events": pagination["page_obj"],
            "can_create_event": True,
            **pagination,
            **filter_ctx,
        },
    )


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event.objects.select_related("org"), id=event_id)

    can_assign = user_can_assign_people(request.user, event)

    # Always get/create the default (hidden) shift
    default_shift = event.default_shift()

    # People already assigned via default shift
    assigned_qs = Person.objects.filter(
        shift_assignments__shift=default_shift,
    ).distinct()

    assigned_ids = set(assigned_qs.values_list("id", flat=True))

    if request.method == "POST" and can_assign:
        posted_ids = set(
            map(int, request.POST.getlist("people")),
        )

        # Remove unchecked people
        ShiftAssignment.objects.filter(
            shift=default_shift,
            person_id__in=(assigned_ids - posted_ids),
        ).delete()

        # Add newly checked people
        ShiftAssignment.objects.bulk_create(
            [
                ShiftAssignment(
                    shift=default_shift,
                    person_id=pid,
                )
                for pid in (posted_ids - assigned_ids)
            ],
            ignore_conflicts=True,
        )

        return redirect("events:event_detail", event.id)

    # Only allow people from the same org
    available_people = Person.objects.filter(
        org_links__org=event.org,
    ).distinct()

    # Paginate visible shifts (excluding hidden default shift if desired)
    shifts_qs = event.shifts.exclude(id=default_shift.id).order_by("starts_at")

    pagination = paginate(request, shifts_qs, per_page=10)

    return render(
        request,
        "events/event_detail.html",
        {
            "event": event,
            "can_edit": user_can_manage_events(request.user, event),
            "can_assign_people": can_assign,
            "assigned_people": assigned_qs,
            "available_people": available_people,
            "shifts": pagination["page_obj"],
            **pagination,
        },
    )


@login_required
def event_create(request):
    # TODO: handle perms better

    org_qs = Organization.objects.filter(
        memberships__user=request.user,
    ).distinct()

    initial = {}
    # Allow redirect forms to specify org
    org_id = request.GET.get("org")
    if org_id:
        try:
            org = org_qs.get(id=org_id)
            initial["org"] = org
        except Organization.DoesNotExist:
            pass

    if request.method == "POST":
        form = EventForm(request.POST, initial=initial)
        form.fields["org"].queryset = org_qs
        if form.is_valid():
            org = form.cleaned_data["org"]

            if not user_can_manage_events(request.user, org=org):
                msg = (
                    "You do not have permission to create events for this organization."
                )
                raise PermissionDenied(msg)

            event = form.save(commit=False)
            event.created_by = request.user
            event.owned_by = request.user
            event.save()
            return redirect("events:event_detail", event.id)
    else:
        form = EventForm(initial=initial)
        form.fields["org"].queryset = org_qs

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "is_create": True,
        },
    )


ShiftFormSet = modelformset_factory(
    Shift,
    form=ShiftForm,
    extra=1,
    can_delete=True,
)


@login_required
def event_edit(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not user_can_manage_events(request.user, event):
        raise Http404

    default_shift = event.default_shift()

    shift_qs = (
        event.shifts.exclude(is_default=True)
        .exclude(is_hidden=True)
        .order_by("starts_at")
    )

    org_qs = Organization.objects.filter(
        memberships__user=request.user,
    ).distinct()

    can_edit_owner = user_can_edit_event_owner(request.user, event)

    if request.method == "POST":
        shift_formset = ShiftFormSet(
            request.POST,
            queryset=shift_qs,
        )
        form = EventForm(request.POST, instance=event)
        if not can_edit_owner:
            form.fields["owned_by"].disabled = True
        form.fields["owned_by"].queryset = User.objects.filter(
            memberships__org=event.org,
        ).distinct()
        form.fields["owned_by"].required = False
        form.fields["org"].queryset = org_qs
        if form.is_valid() and shift_formset.is_valid():
            event = form.save()

            # Update default shift capacity
            default_shift.capacity = request.POST.get("default_shift_capacity") or 0
            default_shift.save()

            shifts = shift_formset.save(commit=False)
            for shift in shifts:
                shift.event = event
                shift.save()

            for shift in shift_formset.deleted_objects:
                shift.delete()

            return redirect("events:event_detail", event.id)
    else:
        shift_formset = ShiftFormSet(queryset=shift_qs)
        form = EventForm(instance=event)
        form.fields["org"].queryset = org_qs
        form.fields["owned_by"].queryset = User.objects.filter(
            memberships__org=event.org,
        ).distinct()
        form.fields["owned_by"].required = False

    return render(
        request,
        "events/event_form.html",
        {
            "form": form,
            "event": event,
            "can_edit_owner": can_edit_owner,
            "default_shift": default_shift,
            "shift_formset": shift_formset,
            "is_create": False,
        },
    )


@login_required
@require_POST
def event_update_times(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if not user_can_manage_events(request.user, event=event):
        return HttpResponseForbidden("You do not have permission to modify this event.")

    start = parse_datetime(request.POST.get("start"))
    end = parse_datetime(request.POST.get("end"))

    if not start or not end:
        return JsonResponse({"error": "Invalid datetime"}, status=400)

    if end <= start:
        return JsonResponse({"error": "End must be after start"}, status=400)

    event.starts_at = start
    event.ends_at = end
    event.save(update_fields=["starts_at", "ends_at"])

    return JsonResponse({"ok": True})


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
