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

from .actions.utils import reset_ticket_actions
from .audit import log_ticket_event
from .filters import TICKET_FILTERS
from .forms import TicketUpdateForm
from .models import Ticket
from .models import TicketAuditEvent
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
    log_ticket_event(
        ticket=ticket,
        event_type=TicketAuditEvent.CLAIMED,
        message=f"Ticket claimed by {request.user}",
        actor=request.user,
    )

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

    reset_ticket_actions(ticket)

    log_ticket_event(
        ticket=ticket,
        event_type=TicketAuditEvent.UNCLAIMED,
        message="Ticket unclaimed",
        actor=request.user,
    )

    messages.success(request, "Ticket has been unassigned.")
    return redirect("tickets:ticket_detail", ticket_id=ticket.id)


@login_required
def update_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method != "POST":
        return redirect("tickets:ticket_detail", ticket_id=ticket.id)

    form = TicketUpdateForm(request.POST, instance=ticket)

    if form.is_valid():
        changed_fields = {
            field: form.cleaned_data[field] for field in form.changed_data
        }

        form.save()

        if changed_fields:
            log_ticket_event(
                ticket=ticket,
                event_type=TicketAuditEvent.UPDATED,
                actor=request.user,
                message="Ticket updated",
                metadata={
                    "changed_fields": changed_fields,
                },
            )
        messages.success(request, "Ticket updated.")
    else:
        log_ticket_event(
            ticket=ticket,
            event_type=TicketAuditEvent.UPDATED,
            actor=request.user,
            success=False,
            message="Ticket update failed due to validation errors",
            metadata={
                "errors": form.errors,
            },
        )

        messages.error(request, f"Please correct the errors: {form.errors}")

    return redirect("tickets:ticket_detail", ticket_id=ticket.id)
