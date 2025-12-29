from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from openvolunteer.tickets.permissions import user_can_run_action

from .models import TicketAction
from .service import TicketActionService


@login_required
@require_POST
def run_action(request, action_id):
    action = get_object_or_404(
        TicketAction.objects.select_related("ticket", "ticket__assigned_to"),
        id=action_id,
    )

    ticket = action.ticket

    if not user_can_run_action(request.user, ticket, ticket.event):
        return HttpResponseForbidden("You are not allowed to perform this action.")

    try:
        TicketActionService.execute(action=action, user=request.user)
        messages.success(request, f"Action '{action.label}' completed.")
    except PermissionError as exc:
        messages.error(request, str(exc))
    except ValueError as exc:
        messages.error(request, str(exc))
    except Exception:
        # Do not leak internals to users
        messages.error(
            request,
            "Something went wrong while performing this action.",
        )
        raise  # re-raise so you still get tracebacks in dev

    return redirect("tickets:ticket_detail", ticket.id)
