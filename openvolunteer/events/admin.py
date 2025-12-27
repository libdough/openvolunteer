#!/usr/bin/env python3
from django.contrib import admin
from django.contrib import messages

from openvolunteer.tickets.services import generate_tickets_for_event

from .models import Event
from .models import EventStatus
from .models import EventTemplate
from .models import Shift
from .models import ShiftAssignment


class ShiftAssignmentInline(admin.TabularInline):
    model = ShiftAssignment
    extra = 0
    autocomplete_fields = ["person"]
    fields = ("person", "checked_in_at")
    readonly_fields = ("checked_in_at",)
    show_change_link = True


class ShiftInline(admin.TabularInline):
    model = Shift
    extra = 0

    fields = (
        "name",
        "starts_at",
        "ends_at",
        "capacity_display",
        "signup_count",
        "is_default",
        "is_hidden",
    )

    readonly_fields = (
        "capacity_display",
        "signup_count",
        "is_default",
        "is_hidden",
    )

    show_change_link = True

    @admin.display(description="Capacity")
    def capacity_display(self, obj):
        return "∞" if obj.capacity == 0 else obj.capacity

    @admin.display(description="Signups")
    def signup_count(self, obj):
        return obj.assignments.count()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(is_hidden=False)


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "starts_at",
        "ends_at",
        "capacity_display",
        "signup_count",
        "is_default",
        "is_hidden",
    )

    list_filter = ("event__org",)
    search_fields = ("name", "event__title")
    ordering = ("starts_at",)

    inlines = [ShiftAssignmentInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("event").prefetch_related("assignments")

    @admin.display(description="Capacity")
    def capacity_display(self, obj):
        return "∞" if obj.capacity == 0 else obj.capacity

    @admin.display(description="Signups")
    def signup_count(self, obj):
        return obj.assignments.count()


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "org",
        "event_status",
        "template",
        "starts_at",
        "ends_at",
        "shift_count",
        "owned_by",
        "created_at",
    )

    list_filter = (
        "org",
        "event_status",
        "template",
        "starts_at",
    )

    search_fields = (
        "title",
        "event_status",
        "template",
        "description",
        "location_name",
        "location_address",
    )
    actions = [
        "make_draft",
        "make_scheduled",
        "make_finished",
        "generate_tickets_from_template",
    ]

    ordering = ("-starts_at",)

    inlines = [ShiftInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "org",
                    "title",
                    "event_status",
                    "template",
                    "owned_by",
                ),
            },
        ),
        (
            "Schedule",
            {
                "fields": (
                    "starts_at",
                    "ends_at",
                ),
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "location_name",
                    "location_address",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Details",
            {
                "fields": ("description",),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by",),
                "classes": ("collapse",),
            },
        ),
    )

    autocomplete_fields = ["org"]
    readonly_fields = ("created_by",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if not obj.owned_by:
            obj.owned_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("shifts")

    @admin.display(description="Shifts")
    def shift_count(self, obj):
        return obj.shifts.count()

    @admin.action(description="Mark selected events as Draft")
    def make_draft(self, request, queryset):
        queryset.update(event_status=EventStatus.DRAFT)

    @admin.action(description="Mark selected events as Scheduled")
    def make_scheduled(self, request, queryset):
        queryset.update(event_status=EventStatus.SCHEDULED)

    @admin.action(description="Mark selected events as Finished")
    def make_finished(self, request, queryset):
        queryset.update(event_status=EventStatus.FINISHED)

    @admin.action(description="Generate tickets from EventTemplate")
    def generate_tickets_from_template(self, request, queryset):
        created = 0
        skipped = 0
        warned = 0

        for event in queryset.select_related("template", "org").prefetch_related(
            "ticket_batches",
        ):
            try:
                if not event.template:
                    skipped += 1
                    messages.warning(
                        request,
                        f"Event '{event}' has no EventTemplate attached.",
                    )
                    continue

                if event.has_ticket_batches():
                    warned += 1
                    messages.warning(
                        request,
                        (
                            f"Event '{event}' already has "
                            f"{event.ticket_batch_count()} ticket batch(es). "
                            "Generating another batch anyway."
                        ),
                    )

                batch, tickets = generate_tickets_for_event(
                    event=event,
                    created_by=request.user,
                    reason="Generated via admin action",
                )

                created += 1
                messages.success(
                    request,
                    f"Created {len(tickets)} tickets for '{event}' "
                    f"(batch: {batch.name})",
                )
            # ruff: noqa: BLE001
            except Exception as exc:
                skipped += 1
                messages.error(
                    request,
                    f"Failed to generate tickets for '{event}': {exc}",
                )

        if created:
            messages.info(
                request,
                f"Ticket generation complete: {created} event(s) processed.",
            )

        if warned:
            messages.warning(
                request,
                "One or more events already had ticket batches. "
                "Review batches to avoid duplicate work.",
            )

        if skipped and not created:
            messages.warning(request, "No tickets were generated.")


@admin.register(EventTemplate)
class EventTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "org",
        "is_active",
        "event_count",
        "ticket_template_count",
        "created_at",
        "modified_at",
    )

    list_filter = (
        "is_active",
        "org",
    )

    search_fields = ("name",)

    filter_horizontal = ("ticket_templates",)

    readonly_fields = (
        "created_at",
        "modified_at",
        "event_count",
        "ticket_template_count",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "org",
                    "name",
                    "is_active",
                ),
            },
        ),
        (
            "Ticket Templates",
            {
                "fields": (
                    "ticket_templates",
                    "ticket_template_count",
                ),
            },
        ),
        (
            "Usage",
            {
                "fields": ("event_count",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
            },
        ),
    )

    @admin.display(
        description="Events using template",
    )
    def event_count(self, obj):
        return obj.events.count()

    @admin.display(
        description="Ticket templates attached",
    )
    def ticket_template_count(self, obj):
        return obj.ticket_templates.count()
