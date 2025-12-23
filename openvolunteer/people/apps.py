#!/usr/bin/env python3
from django.apps import AppConfig


class PeopleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "openvolunteer.people"
    verbose_name = "People & Contacts"
