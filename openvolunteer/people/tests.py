#!/usr/bin/env python3
from django.contrib.auth import get_user_model
from django.test import TestCase
from orgs.models import Membership
from orgs.models import Organization

from .models import Person

User = get_user_model()


class PersonModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )
        self.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )
        Membership.objects.create(
            user=self.user,
            org=self.org,
            role="admin",
        )

    def test_create_person(self):
        person = Person.objects.create(
            org=self.org,
            full_name="Jane Doe",
            email="jane@example.com",
        )
        self.assertEqual(person.org, self.org)
        self.assertEqual(person.full_name, "Jane Doe")
