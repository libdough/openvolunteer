#!/usr/bin/env python3
# people/models.py
import uuid

from django.db import models

from openvolunteer.orgs.models import Organization


class Person(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    attributes = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["full_name"]),
            models.Index(fields=["email"]),
            models.Index(fields=["phone"]),
        ]

    def __str__(self):
        return self.full_name


class PersonOrganizationRole(models.TextChoices):
    MEMBER = "member", "Member"
    VOLUNTEER = "volunteer", "Volunteer"
    LEAD = "lead", "Lead"
    STAFF = "staff", "Staff"


class PersonOrganization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="org_links",
    )
    org = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="people_links",
    )

    role = models.CharField(
        max_length=20,
        choices=PersonOrganizationRole,
        default=PersonOrganizationRole.VOLUNTEER,
    )

    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("person", "org")]
        indexes = [
            models.Index(fields=["org", "role"]),
            models.Index(fields=["person", "org"]),
        ]
        verbose_name = "Org Membership"
        verbose_name_plural = "Org Memberships"

    def __str__(self):
        return f"{self.org.name} ({self.role})"


class PersonTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Make org optional
    org = models.ForeignKey(
        "orgs.Organization",
        on_delete=models.CASCADE,
        related_name="person_tags",
        blank=True,
        null=True,
    )

    name = models.CharField(max_length=64)

    class TagColor(models.TextChoices):
        RED = "red", "Red"
        ORANGE = "orange", "Orange"
        YELLOW = "yellow", "Yellow"
        GREEN = "green", "Green"
        BLUE = "blue", "Blue"
        PURPLE = "purple", "Purple"
        GREY = "grey", "Grey"

    color = models.CharField(
        max_length=16,
        choices=TagColor.choices,
        default=TagColor.GREY,
    )

    class Meta:
        unique_together = [("org", "name")]  # still unique per org, NULLs can repeat

    def __str__(self):
        if self.org:
            return f"{self.name} ({self.org.name})"
        return f"{self.name} (Global)"


class PersonTagging(models.Model):
    """
    Application of a tag to a person by an organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="taggings",
    )

    tag = models.ForeignKey(
        PersonTag,
        on_delete=models.CASCADE,
        related_name="taggings",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("person", "tag")]
        indexes = [
            models.Index(fields=["person"]),
            models.Index(fields=["tag"]),
        ]

    def __str__(self):
        if self.tag.org:
            return f"{self.tag.name} ({self.tag.org.name})"
        return f"{self.tag.name} (Global)"
