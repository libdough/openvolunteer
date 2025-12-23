#!/usr/bin/env python3
from django.contrib import admin

from .models import Event
from .models import Shift
from .models import ShiftSignup


class ShiftSignupInline(admin.TabularInline):
    model = ShiftSignup
    extra = 0
    autocomplete_fields = ["person"]
    fields = ("person", "checked_in_at", "notes")
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
    )

    readonly_fields = (
        "capacity_display",
        "signup_count",
    )

    show_change_link = True

    @admin.display(description="Capacity")
    def capacity_display(self, obj):
        return "∞" if obj.capacity == 0 else obj.capacity

    @admin.display(description="Signups")
    def signup_count(self, obj):
        return obj.signups.count()


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event",
        "starts_at",
        "ends_at",
        "capacity_display",
        "signup_count",
    )

    list_filter = ("event__org",)
    search_fields = ("name", "event__title")
    ordering = ("starts_at",)

    inlines = [ShiftSignupInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("event").prefetch_related("signups")

    @admin.display(description="Capacity")
    def capacity_display(self, obj):
        return "∞" if obj.capacity == 0 else obj.capacity

    @admin.display(description="Signups")
    def signup_count(self, obj):
        return obj.signups.count()


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "org",
        "event_type",
        "starts_at",
        "ends_at",
        "shift_count",
        "created_at",
    )

    list_filter = (
        "org",
        "event_type",
        "starts_at",
    )

    search_fields = (
        "title",
        "description",
        "location_name",
        "location_address",
    )

    ordering = ("-starts_at",)

    inlines = [ShiftInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "org",
                    "title",
                    "event_type",
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
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("shifts")

    @admin.display(description="Shifts")
    def shift_count(self, obj):
        return obj.shifts.count()
