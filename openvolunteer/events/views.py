#!/usr/bin/env python3
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.views.generic import DetailView
from django.views.generic import ListView

from .forms import ShiftSignupForm
from .models import Event
from .models import Shift
from .models import ShiftSignup


class EventListView(ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"
    ordering = ("starts_at",)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("org").prefetch_related("shifts")


class EventDetailView(DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("org")
            .prefetch_related("shifts__signups", "shifts__signups__person")
        )


@login_required
def shift_signup(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)

    if request.method == "POST":
        form = ShiftSignupForm(request.POST)
        if form.is_valid():
            ShiftSignup.objects.get_or_create(
                shift=shift,
                person=request.user.person,
                defaults=form.cleaned_data,
            )
            messages.success(request, "You are signed up!")
            return redirect("events:event_detail", pk=shift.event_id)
    else:
        form = ShiftSignupForm()

    return render(
        request,
        "events/shift_signup.html",
        {
            "shift": shift,
            "form": form,
        },
    )
