#!/usr/bin/env python3
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.orgs.queryset import orgs_for_user

from .filters import TICKET_FILTERS
from .forms import TicketUpdateForm
from .models import Ticket
from .models import TicketStatus


@login_required
def ticket_list(request):
    tickets = (
        Ticket.objects.select_related("event", "batch", "assigned_to", "person")
        .filter(org__in=orgs_for_user(request.user))
        .distinct()
        .order_by("priority", "-created_at")
    )

    tickets, filter_ctx = apply_filters(request, tickets, TICKET_FILTERS)
    pagination = paginate(request, tickets, per_page=20)

    return render(
        request,
        "tickets/ticket_list.html",
        {
            "tickets": pagination["page_obj"],
            **pagination,
            **filter_ctx,
        },
    )


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            "event",
            "batch",
            "assigned_to",
            "person",
        ),
        id=ticket_id,
    )

    form = TicketUpdateForm(instance=ticket)

    return render(
        request,
        "tickets/ticket_detail.html",
        {
            "ticket": ticket,
            "form": form,
        },
    )


@login_required
def claim_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if not ticket.claimable:
        return HttpResponseForbidden("This ticket is not claimable.")

    if ticket.assigned_to:
        messages.warning(request, "Ticket is already assigned.")
        return redirect("tickets:ticket_detail", ticket_id=ticket.id)

    ticket.assigned_to = request.user
    ticket.status = TicketStatus.TODO
    ticket.save()

    messages.success(request, "You have claimed this ticket.")
    return redirect("tickets:ticket_detail", ticket_id=ticket.id)


@login_required
def unclaim_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if ticket.assigned_to != request.user:
        return HttpResponseForbidden("You cannot unclaim this ticket.")

    ticket.assigned_to = None
    if not ticket.is_closed:
        ticket.status = TicketStatus.OPEN
    ticket.save()

    messages.success(request, "Ticket has been unassigned.")
    return redirect("tickets:ticket_detail", ticket_id=ticket.id)


@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method != "POST":
        return redirect("tickets:ticket_detail", ticket_id=ticket.id)

    form = TicketUpdateForm(request.POST, instance=ticket)

    if form.is_valid():
        form.save()
        messages.success(request, "Ticket updated.")
    else:
        messages.error(request, f"Please correct the errors: {form.errors}")

    return redirect("tickets:ticket_detail", ticket_id=ticket.id)
