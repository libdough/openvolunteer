#!/usr/bin/env python3
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from openvolunteer.orgs.models import Organization
from openvolunteer.people.models import Person


class ActivityKind(models.TextChoices):
    NOTE = "note", "Note"
    CALL = "call", "Call"
    TEXT = "text", "Text"
    KNOCK = "knock", "Door Knock"
    EMAIL = "email", "Email"
    EVENT_CHECKIN = "event_checkin", "Event Check-in"
    CUSTOM = "custom", "Custom"


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    kind = models.CharField(max_length=30, choices=ActivityKind)

    # Who did it (staff/volunteer user)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="activities",
    )

    # Who it was about (usually a Person)
    person = models.ForeignKey(
        Person,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activities",
    )

    # Optional generic “related object” hook (Event, Shift, etc.)
    related_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    related_object_id = models.UUIDField(null=True, blank=True)
    related_object = GenericForeignKey("related_content_type", "related_object_id")

    occurred_at = models.DateTimeField()
    summary = models.CharField(max_length=200, blank=True)
    details = models.TextField(blank=True)

    # For call outcomes, canvass script answers, dispositions, etc.
    data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["org", "occurred_at"]),
            models.Index(fields=["org", "kind"]),
            models.Index(fields=["org", "person", "occurred_at"]),
        ]

    def __str__(self):
        return f"{self.actor} {self.kind} with {self.person}"
