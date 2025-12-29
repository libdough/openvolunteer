#!/usr/bin/env python3
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class EventsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openvolunteer.events"
    verbose_name = "Events"

    def ready(self):
        # ruff: noqa: PLC0415

        from .defaults import install_default_tasks

        def install_defaults(sender, **kwargs):
            install_default_tasks()

        post_migrate.connect(install_defaults, sender=self)
