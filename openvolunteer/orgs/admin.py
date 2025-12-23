#!/usr/bin/env python3
from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    search_fields = ("name", "slug")
    list_display = ("name", "slug", "created_at")
    prepopulated_fields = {"slug": ("name",)}
