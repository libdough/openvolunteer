#!/usr/bin/env python3
from django.apps import AppConfig
from django.db.models.signals import post_migrate


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openvolunteer.tickets"
    verbose_name = "Tickets"

    def ready(self):
        # ruff: noqa: PLC0415
        # Make sure recievers are registered

        from .defaults import install_default_event_templates
        from .defaults import install_default_tasks
        from .defaults import install_default_ticket_actions
        from .defaults import install_default_ticket_templates

        def install_defaults(sender, **kwargs):
            actions = install_default_ticket_actions()
            ticket_templates = install_default_ticket_templates(actions)
            install_default_event_templates(ticket_templates)
            install_default_tasks()

        post_migrate.connect(install_defaults, sender=self)
