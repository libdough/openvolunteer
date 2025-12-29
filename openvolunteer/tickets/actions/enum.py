from django.db import models


class TicketActionButtonColor(models.TextChoices):
    PRIMARY = "primary", "Primary (blue)"
    DANGER = "danger", "Danger (red)"
    SECONDARY = "secondary", "Secondary (gray)"
    SUCCESS = "success", "Success (green)"
    WARNING = "warning", "Warning (yellow)"
    LINK = "link", "link (no-color)"


class TicketActionType(models.TextChoices):
    NOOP = "noop", "No-op (ticket status changes only)"
    UPDATE_SHIFT_STATUS = "update_shift_status", "Update shift assignment status"
    UPSERT_SHIFT_ASSIGNMENT = "upsert_shift_assignment", "Upsert shift assignment"
    UPDATE_EVENT_STATUS = "update_event_status", "Update event status"
    UPSERT_TAG = "upsert_tag", "Upsert tag on person"
    REMOVE_TAG = "remove_tag", "Remove tag from person"


class TicketActionRunWhen(models.TextChoices):
    MANUAL = "manual", "Manual"
    ON_CREATE = "on_create", "On ticket creation"
    ON_CLAIM = "on_claim", "On ticket claim"
    ON_UNCLAIM = "on_unclaim", "On ticket unclaim"
    ON_UPDATE = "on_update", "On ticket update"
