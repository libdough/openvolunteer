#!/usr/bin/env python3
# events/models.py
import uuid

from django.conf import settings
from django.db import models

from openvolunteer.orgs.models import Organization


class EventType(models.TextChoices):
    CANVASS = "canvass", "Canvass"
    PHONEBANK = "phonebank", "Phone Bank"
    TRAINING = "training", "Training"
    MEETUP = "meetup", "Meetup"
    OTHER = "other", "Other"


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    FINISHED = "finished", "Finished"


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="events",
    )
    title = models.CharField(max_length=200)
    event_status = models.CharField(
        max_length=20,
        choices=EventStatus,
        default=EventStatus.DRAFT,
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType,
        default=EventType.OTHER,
    )

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    location_name = models.CharField(max_length=200, blank=True)
    location_address = models.CharField(max_length=300, blank=True)

    description = models.TextField(blank=True)
    owned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_owned",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="events_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Shift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="shifts")
    name = models.CharField(max_length=200, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(
        default=0,
        help_text="Set to 0 for unlimited capacity",
    )

    def __str__(self):
        return self.name

    @property
    def assigned_count(self):
        return self.assignments.count()

    @property
    def has_capacity(self):
        if self.capacity == 0:
            return True
        return self.assigned_count < self.capacity


class ShiftAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        "Shift",
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    person = models.ForeignKey(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="shift_assignments",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    checked_in_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("shift", "person")]
        indexes = [
            models.Index(fields=["shift"]),
            models.Index(fields=["person"]),
        ]

    def __str__(self):
        return f"{self.person.full_name} → {self.shift}"
