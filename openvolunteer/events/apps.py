#!/usr/bin/env python3
from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openvolunteer.events"
    verbose_name = "Events"
