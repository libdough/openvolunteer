from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Value
from django.db.models import When

from .models import Ticket
from .models import TicketStatus


def get_filtered_tickets(  # noqa: PLR0913
    *,
    org=None,
    event=None,
    person=None,
    shift=None,
    status=None,
    exclude_statuses=None,
    claimed_by=None,
    limit=10,
):
    qs = Ticket.objects.all()
    claim_qs = {}

    if org:
        qs = qs.filter(org=org)
        claim_qs["org"] = org.id
    if event:
        qs = qs.filter(event=event)
        claim_qs["event"] = event.id
    if person:
        qs = qs.filter(person=person)
        claim_qs["person"] = person.id
    if shift:
        qs = qs.filter(shift=shift)
        claim_qs["shift"] = shift.id
    if status:
        qs = qs.filter(status=status)
    if exclude_statuses:
        qs = qs.exclude(status__in=exclude_statuses)
        claim_qs["exclude_statuses"] = ",".join(exclude_statuses)
    if claimed_by:
        qs = qs.filter(assigned_to=claimed_by)

    ctx = {}
    if claim_qs:
        ctx["ticket_querystring"] = "&".join(f"{k}={v}" for k, v in claim_qs.items())

    tickets = (
        qs.select_related("assigned_to", "reporter")
        .annotate(
            finished_sort=Case(
                When(status=TicketStatus.OPEN, then=Value(0)),
                When(claimable=False, then=Value(1)),
                When(
                    status__in=[TicketStatus.COMPLETED, TicketStatus.CANCELED],
                    then=Value(3),
                ),
                default=Value(2),
                output_field=IntegerField(),
            ),
        )
        .order_by("finished_sort", "priority", "-created_at")[:limit]
    )

    ctx["tickets"] = tickets
    ctx["ticket_count"] = qs.count()

    return ctx
