# events/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Event
from .models import Shift


@receiver(post_save, sender=Event)
def create_default_shift(sender, instance, created, **kwargs):
    if not created:
        return

    Shift.objects.create(
        event=instance,
        name="",
        starts_at=instance.starts_at,
        ends_at=instance.ends_at,
        capacity=0,  # unlimited
        is_default=True,
        is_hidden=True,
    )
