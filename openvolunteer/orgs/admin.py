#!/usr/bin/env python3
from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Membership
from .models import Organization

User = get_user_model()


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ["user"]
    fields = ("user", "role", "is_active")
    verbose_name = "Member"
    verbose_name_plural = "Members"


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "created_at")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("org", "user", "role", "is_active", "created_at")
    list_filter = ("org", "role", "is_active")
    search_fields = ("org__name", "user__username", "user__email")
    autocomplete_fields = ("org", "user")
