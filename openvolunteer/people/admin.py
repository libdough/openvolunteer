#!/usr/bin/env python3
from django.contrib import admin
from django.utils.html import format_html
from django.utils.html import format_html_join

from .models import Person
from .models import PersonOrganization
from .models import PersonTag
from .models import PersonTagging


# Inline for editing tags on a Person
class PersonTaggingInline(admin.TabularInline):
    model = PersonTagging
    extra = 0
    autocomplete_fields = ["tag"]
    verbose_name = "Tag"
    verbose_name_plural = "Tags"
    fields = ("tag", "tag_colored")  # Use a custom readonly field
    readonly_fields = ("tag_colored",)

    @admin.display(
        description="Tag",
    )
    def tag_colored(self, obj):
        if obj.tag:
            return format_html(
                '<span style="display:inline-block; padding:2px 6px; '
                'background-color:{}; color:#fff; border-radius:3px;">{}</span>',
                self._color_to_hex(obj.tag.color),
                obj.tag.name,
            )
        return ""

    def _color_to_hex(self, color_name):
        # Map the named colors to actual hex codes
        mapping = {
            "red": "#f44336",
            "orange": "#ff9800",
            "yellow": "#ffeb3b",
            "green": "#4caf50",
            "blue": "#2196f3",
            "purple": "#9c27b0",
            "grey": "#9e9e9e",
        }
        return mapping.get(color_name, "#9e9e9e")


# Inline for org memberships
class PersonOrganizationInline(admin.TabularInline):
    model = PersonOrganization
    extra = 0
    autocomplete_fields = ["org"]
    fields = ("org", "role", "is_active")
    show_change_link = True
    verbose_name = "Org Membership"
    verbose_name_plural = "Org Memberships"


class OrganizationMembershipFilter(admin.SimpleListFilter):
    title = "Organization"
    parameter_name = "org"

    def lookups(self, request, model_admin):
        qs = (
            PersonOrganization.objects.select_related("org")
            .order_by("org__name")
            .values_list("org_id", "org__name")
            .distinct()
        )
        return [(org_id, name) for org_id, name in qs]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                org_links__org_id=self.value(),
                org_links__is_active=True,
            )
        return queryset


class TagMembershipFilter(admin.SimpleListFilter):
    title = "Tag"
    parameter_name = "tag"

    def lookups(self, request, model_admin):
        qs = PersonTag.objects.select_related("org").order_by("name")

        return [
            (tag.id, f"{tag.name} ({tag.org.name})") if tag.org else (tag.id, tag.name)
            for tag in qs
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                taggings__tag_id=self.value(),
            )
        return queryset


# Person admin with inlines
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "discord",
        "email",
        "phone",
        "tags_display",
        "created_at",
    )
    search_fields = ("full_name", "discord", "email", "phone")
    ordering = ("full_name",)
    list_filter = (
        OrganizationMembershipFilter,
        TagMembershipFilter,
    )
    inlines = [
        PersonOrganizationInline,
        PersonTaggingInline,
    ]
    fieldsets = (
        (None, {"fields": ("full_name", "discord", "email", "phone")}),
        (
            "Address",
            {
                "fields": (
                    "address_line1",
                    "address_line2",
                    "city",
                    "state",
                    "postal_code",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Metadata", {"fields": ("attributes",), "classes": ("collapse",)}),
    )

    @admin.display(description="Tags")
    def tags_display(self, obj):
        if not obj.taggings.exists():
            return "—"

        return format_html_join(
            "",
            '<span style="display:inline-block; padding:2px 6px; margin:1px; '
            'background-color:{}; color:#fff; border-radius:3px; font-size:11px;">'
            "{}</span>",
            (
                (
                    self._color_to_hex(tagging.tag.color),
                    tagging.tag.name,
                )
                for tagging in obj.taggings.all()
                if tagging.tag
            ),
        )

    def _color_to_hex(self, color_name):
        mapping = {
            "red": "#f44336",
            "orange": "#ff9800",
            "yellow": "#ffeb3b",
            "green": "#4caf50",
            "blue": "#2196f3",
            "purple": "#9c27b0",
            "grey": "#9e9e9e",
        }
        return mapping.get(color_name, "#9e9e9e")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "org_links__org",
            "taggings__tag",
        )


@admin.register(PersonTag)
class PersonTagAdmin(admin.ModelAdmin):
    list_display = ("name", "org", "color")
    list_filter = ("org", "color")
    search_fields = ("name", "org__name")

    @admin.display(
        description="Organization",
    )
    def org_display(self, obj):
        return obj.org.name if obj.org else "Global"
