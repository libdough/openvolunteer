#!/usr/bin/env python3
# events/models.py
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Count
from django.db.models import Q

from openvolunteer.orgs.models import Organization


class EventTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    org = models.ForeignKey(
        Organization,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="event_templates",
    )

    name = models.CharField(max_length=200)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    ticket_templates = models.ManyToManyField(
        "tickets.TicketTemplate",
        blank=True,
        related_name="event_templates",
    )

    class Meta:
        unique_together = ("org", "name")

    def __str__(self):
        return self.name


class EventStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    FINISHED = "finished", "Finished"
    CANCELED = "canceled", "Canceled"


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
    template = models.ForeignKey(
        EventTemplate,
        on_delete=models.PROTECT,
        related_name="events",
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
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["event_status", "modified_at"]),
        ]

    def __str__(self):
        return self.title

    def default_shift(self, annotate=True):  # noqa: FBT002
        shift, _ = self.shifts.get_or_create(
            is_default=True,
            defaults={
                "name": self.title,
                "starts_at": self.starts_at,
                "ends_at": self.ends_at,
                "capacity": 0,
                "is_hidden": True,
            },
        )
        if not annotate:
            return shift
        return self.shifts.with_assignment_breakdown().get(id=shift.id)

    @property
    def display_type(self):
        if self.template:
            return self.template.name
        return self.get_event_type_display()

    def visible_shifts(self):
        return self.shifts.filter(is_hidden=False)

    def has_generated_tickets(self):
        return self.ticket_batches.exists()

    def has_ticket_batches(self):
        return self.ticket_batches.exists()

    def ticket_batch_count(self):
        return self.ticket_batches.count()


class ShiftQuerySet(models.QuerySet):
    def with_assignment_breakdown(self):
        return self.annotate(
            assignments_init=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.INIT),
            ),
            assignments_pending=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.PENDING),
            ),
            assignments_declined=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.DECLINED),
            ),
            assignments_partial=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.PARTIAL),
            ),
            assignments_confirmed=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.CONFIRMED),
            ),
            assignments_signedin=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.SIGNEDIN),
            ),
            assignments_noshow=Count(
                "assignments",
                filter=Q(assignments__status=ShiftAssignmentStatus.NOSHOW),
            ),
        )


class Shift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="shifts")

    name = models.CharField(max_length=200, blank=True)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    capacity = models.PositiveIntegerField(default=0)  # 0 = unlimited

    is_default = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)

    objects = ShiftQuerySet.as_manager()

    class Meta:
        indexes = [
            models.Index(fields=["event", "is_default"]),
        ]

    def __str__(self):
        if self.is_default:
            return "Default event shift"
        return self.name or "Shift"

    @property
    def assigned_count(self):
        return self.assignments.count()

    @property
    def status_counts(self):
        """
        Requires `with_assignment_breakdown()` to have been applied.
        Safe fallback to 0 for unannotated shifts.
        """

        class Counts:
            init = getattr(self, "assignments_init", 0)
            pending = getattr(self, "assignments_pending", 0)
            declined = getattr(self, "assignments_declined", 0)
            partial = getattr(self, "assignments_partial", 0)
            confirmed = getattr(self, "assignments_confirmed", 0)
            signedin = getattr(self, "signedin", 0)
            no_show = getattr(self, "assignments_noshow", 0)

        return Counts()

    @property
    def has_capacity(self):
        if self.capacity == 0:
            return True
        return self.assigned_count < self.capacity

    @property
    def is_new_record(self):
        return self._state.adding


class ShiftAssignmentStatus(models.TextChoices):
    INIT = "init", "Initialized"
    PENDING = "pending", "Pending confirmation"
    DECLINED = "declined", "Declined"
    PARTIAL = "partial", "Partially committed"
    CONFIRMED = "confirmed", "Fully committed"
    SIGNEDIN = "sgined_in", "Signed In"
    NOSHOW = "no_show", "No Show"


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

    status = models.CharField(
        max_length=20,
        choices=ShiftAssignmentStatus,
        default=ShiftAssignmentStatus.INIT,
        db_index=True,
    )

    checked_in_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("shift", "person")]
        indexes = [
            models.Index(fields=["shift"]),
            models.Index(fields=["person"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.person.full_name} <-> {self.shift} ({self.get_status_display()})"
