#!/usr/bin/env python3
from django.contrib import admin

from .models import Event
from .models import EventStatus
from .models import Shift
from .models import ShiftAssignment


@admin.action(description="Mark selected events as Draft")
def make_draft(modeladmin, request, queryset):
    queryset.update(event_status=EventStatus.DRAFT)


@admin.action(description="Mark selected events as Scheduled")
def make_scheduled(modeladmin, request, queryset):
    queryset.update(event_status=EventStatus.SCHEDULED)


@admin.action(description="Mark selected events as Finished")
def make_finished(modeladmin, request, queryset):
    queryset.update(event_status=EventStatus.FINISHED)


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
        "event_type",
        "starts_at",
        "ends_at",
        "shift_count",
        "owned_by",
        "created_at",
    )

    list_filter = (
        "org",
        "event_status",
        "event_type",
        "starts_at",
    )

    search_fields = (
        "title",
        "event_status",
        "event_type",
        "description",
        "location_name",
        "location_address",
    )
    actions = [make_draft, make_scheduled, make_finished]

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
                    "event_type",
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
