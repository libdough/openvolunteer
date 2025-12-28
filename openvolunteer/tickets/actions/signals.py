from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .enum import TicketActionRunWhen
from .models import TicketAction
from .service import TicketActionService


@receiver(post_save, sender=TicketAction)
def run_on_create_actions(sender, instance, created, **kwargs):
    if not created:
        return

    # Only run ON_CREATEs
    if instance.run_when != TicketActionRunWhen.ON_CREATE:
        return

    # Only run if not completed
    if instance.is_completed:
        return

    transaction.on_commit(
        lambda: TicketActionService.execute(
            action=instance,
            user=instance.ticket.reporter,
        ),
    )
