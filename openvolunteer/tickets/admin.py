#!/usr/bin/env python3
from django.contrib import admin
from django.utils.html import format_html

from .actions.models import TicketActionTemplate
from .models import Ticket
from .models import TicketBatch
from .models import TicketStatus
from .models import TicketTemplate

# --------------------
# TicketTemplate Admin
# --------------------


@admin.register(TicketTemplate)
class TicketTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "org",
        "default_priority",
        "claimable",
        "is_active",
        "event_template_count",
        "modified_at",
    )
    search_fields = ("name",)
    filter_horizontal = ("action_templates",)

    readonly_fields = (
        "created_at",
        "modified_at",
        "event_template_count",
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
            "Templates",
            {
                "fields": (
                    "ticket_name_template",
                    "description_template",
                ),
            },
        ),
        (
            "Actions",
            {
                "fields": ("action_templates",),
                "description": (
                    "Actions define what the assigned user can do from tickets "
                    "created from this template."
                ),
            },
        ),
        (
            "Behavior",
            {
                "fields": (
                    "default_priority",
                    "claimable",
                    "max_tickets",
                ),
            },
        ),
        (
            "Usage",
            {
                "fields": ("event_template_count",),
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
        description="Used by event templates",
    )
    def event_template_count(self, obj):
        return obj.event_templates.count()


# --------------------
# TicketBatch Admin
# --------------------


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    fields = (
        "name",
        "status",
        "priority",
        "assigned_to",
    )
    readonly_fields = ("name",)


@admin.register(TicketBatch)
class TicketBatchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "org",
        "event",
        "ticket_count",
        "claimable",
        "created_by",
        "created_at",
    )

    list_filter = (
        "org",
        "claimable",
    )

    search_fields = (
        "name",
        "reason",
    )

    readonly_fields = ("created_at",)

    inlines = [TicketInline]

    actions = [
        "mark_all_open",
        "mark_all_canceled",
        "unassign_all",
    ]

    @admin.display(
        description="Tickets",
    )
    def ticket_count(self, obj):
        return obj.tickets.count()

    # ---------
    # Actions
    # ---------

    @admin.action(description="Mark all tickets as OPEN (unassign)")
    def mark_all_open(self, request, queryset):
        for batch in queryset:
            batch.tickets.update(
                status=TicketStatus.OPEN,
                assigned_to=None,
            )

    @admin.action(description="Cancel all tickets")
    def mark_all_canceled(self, request, queryset):
        for batch in queryset:
            batch.tickets.update(status=TicketStatus.CANCELED)

    @admin.action(description="Unassign all tickets")
    def unassign_all(self, request, queryset):
        for batch in queryset:
            batch.tickets.update(assigned_to=None)


# --------------------
# Ticket Admin
# --------------------


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "org",
        "status_badge",
        "priority",
        "assigned_to",
        "event",
        "batch",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "org",
        "claimable",
    )

    search_fields = (
        "name",
        "description",
        "instructions",
    )

    readonly_fields = (
        "created_at",
        "modified_at",
        "completed_at",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "org",
                    "name",
                    "status",
                    "priority",
                ),
            },
        ),
        (
            "Assignment",
            {
                "fields": (
                    "assigned_to",
                    "claimable",
                    "reporter",
                ),
            },
        ),
        (
            "Context",
            {
                "fields": (
                    "event",
                    "person",
                    "batch",
                ),
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "description",
                    "instructions",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                    "completed_at",
                ),
            },
        ),
    )

    actions = [
        "mark_open",
        "mark_todo",
        "mark_inprogress",
        "mark_completed",
        "mark_canceled",
        "unassign",
    ]

    # ----------------
    # Display helpers
    # ----------------

    @admin.display(
        description="Status",
    )
    def status_badge(self, obj):
        color = {
            TicketStatus.OPEN: "secondary",
            TicketStatus.TODO: "primary",
            TicketStatus.INPROGRESS: "warning",
            TicketStatus.BLOCKED: "danger",
            TicketStatus.COMPLETED: "success",
            TicketStatus.CANCELED: "dark",
        }.get(obj.status, "light")

        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display(),
        )

    # ---------
    # Actions
    # ---------

    @admin.action(description="Mark as OPEN (unassign)")
    def mark_open(self, request, queryset):
        queryset.update(status=TicketStatus.OPEN, assigned_to=None)

    @admin.action(description="Mark as TODO")
    def mark_todo(self, request, queryset):
        queryset.update(status=TicketStatus.TODO)

    @admin.action(description="Mark as IN PROGRESS")
    def mark_inprogress(self, request, queryset):
        queryset.update(status=TicketStatus.INPROGRESS)

    @admin.action(description="Mark as COMPLETED")
    def mark_completed(self, request, queryset):
        queryset.update(status=TicketStatus.COMPLETED)

    @admin.action(description="Mark as CANCELED")
    def mark_canceled(self, request, queryset):
        queryset.update(status=TicketStatus.CANCELED)

    @admin.action(description="Unassign tickets")
    def unassign(self, request, queryset):
        queryset.update(assigned_to=None)


@admin.register(TicketActionTemplate)
class TicketActionTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "action_type",
        "button_color",
        "updates_ticket_status",
        "is_active",
    )
    list_filter = (
        "action_type",
        "is_active",
    )
    search_fields = (
        "label",
        "description",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "label",
                    "action_type",
                    "button_color",
                    "description",
                    "is_active",
                ),
            },
        ),
        (
            "Behavior",
            {
                "fields": (
                    "config",
                    "updates_ticket_status",
                ),
                "description": (
                    "Configure how this action behaves and whether it updates "
                    "the ticket status when completed."
                ),
            },
        ),
    )
