#!/usr/bin/env python3
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from openvolunteer.core.filters import apply_filters
from openvolunteer.core.pagination import paginate
from openvolunteer.events.forms import GenerateTicketsForTemplateForm
from openvolunteer.events.models import Event
from openvolunteer.events.models import Shift
from openvolunteer.events.permissions import user_can_manage_events
from openvolunteer.orgs.queryset import orgs_for_user
from openvolunteer.people.models import Person

from .actions.enum import TicketActionRunWhen
from .actions.service import TicketActionService
from .actions.utils import reset_ticket_actions
from .audit import log_ticket_event
from .filters import TICKET_FILTERS
from .forms import TicketUpdateForm
from .models import Ticket
from .models import TicketAuditEvent
from .models import TicketStatus
from .services import generate_tickets_for_event


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
def generate_tickets_for_event_template(request, event_id, template_id):
    event = get_object_or_404(
        Event.objects.select_related("org", "template"),
        id=event_id,
    )

    if not user_can_manage_events(request.user, event):
        msg = "User can not generate tickets for this event"
        raise PermissionDenied(msg)

    shift_id = request.GET.get("shift_id")
    shift = Shift.objects.get(id=shift_id) if shift_id else event.default_shift()

    ticket_template = get_object_or_404(
        event.template.ticket_templates.filter(is_active=True),
        id=template_id,
    )

    # People scoped to this event's org
    people_qs = Person.objects.filter(
        org_links__org=event.org,
        org_links__is_active=True,
        shift_assignments__shift__event=event,
    )
    # Limit to shift
    if shift_id:
        people_qs.filter(
            shift_assignments__shift=shift,
        )
    people_qs = people_qs.distinct()

    shifts = event.shifts.with_assignment_breakdown()

    form = GenerateTicketsForTemplateForm(
        event=event,
        people_queryset=people_qs,
        shifts=shifts,
        data=request.POST or None,
    )

    if request.method == "POST" and form.is_valid():
        generate_tickets_for_event(
            event=event,
            shift=shift,
            created_by=request.user,
            ticket_templates=[ticket_template],
            person_queryset=form.cleaned_data["people"],
            batch_name=form.cleaned_data.get("batch_name"),
            include_default_shift=form.cleaned_data.get("shift") is None,
            reason=f"Generated via event UI ({ticket_template.name})",
        )

        messages.success(
            request,
            f"Tickets generated using “{ticket_template.name}”.",
        )
        return redirect("events:event_detail", event.id)

    return render(
        request,
        "tickets/generate_for_event_template.html",
        {
            "shift": shift,
            "event": event,
            "org": event.org,
            "ticket_template": ticket_template,
            "form": form,
            "people_queryset": people_qs,
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

    # Run on claim actions
    for action in ticket.actions.filter(
        run_when=TicketActionRunWhen.ON_CLAIM,
        is_completed=False,
    ):
        TicketActionService.execute(
            action=action,
            user=request.user,
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

    # Run on unclaim actions
    for action in ticket.actions.filter(
        run_when=TicketActionRunWhen.ON_UNCLAIM,
        is_completed=False,
    ):
        TicketActionService.execute(
            action=action,
            user=request.user,
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
