#!/usr/bin/env python3
from django.apps import AppConfig


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openvolunteer.tickets"
    verbose_name = "Tickets"
