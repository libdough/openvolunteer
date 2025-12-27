import csv
import io

from django.db import transaction

from openvolunteer.orgs.models import Organization
from openvolunteer.orgs.permissions import user_can_manage_people

from .models import Person
from .models import PersonOrganization
from .models import PersonTag
from .models import PersonTagging


@transaction.atomic
def create_person(*, data: dict) -> Person:
    return Person.objects.create(
        **data,
    )


@transaction.atomic
def set_person_tags(*, person: Person, tag_names: list[str]) -> None:
    PersonTagging.objects.filter(person=person).delete()

    for name in tag_names:
        tag, _ = PersonTag.objects.get_or_create(
            org=person.org,
            name=name.strip(),
        )
        PersonTagging.objects.create(
            person=person,
            tag=tag,
        )


@transaction.atomic
def handle_person_csv(user, uploaded_file):
    decoded = uploaded_file.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    allowed_orgs = {
        org.name: org
        for org in Organization.objects.all()
        if user_can_manage_people(user, org)
    }

    created = 0
    skipped = 0

    for row in reader:
        full_name = (row.get("full_name") or "").strip()
        if not full_name:
            skipped += 1
            continue

        email = (row.get("email") or "").strip()

        # Optional de-dupe by email
        if email and Person.objects.filter(email=email).exists():
            skipped += 1
            continue

        person = Person.objects.create(
            full_name=full_name,
            email=email,
            phone=row.get("phone", "").strip(),
            discord=row.get("discord", "").strip(),
        )

        # --- Organizations ---
        org_names = row.get("orgs", "")
        for name in [n.strip() for n in org_names.split("|") if n.strip()]:
            org = allowed_orgs.get(name)
            if org:
                PersonOrganization.objects.get_or_create(
                    person=person,
                    org=org,
                )

        # --- Tags ---
        tag_names = row.get("tags", "")
        for name in [n.strip() for n in tag_names.split("|") if n.strip()]:
            tag, _ = PersonTag.objects.get_or_create(
                name=name,
                org=None,  # global tag by default
            )
            PersonTagging.objects.get_or_create(
                person=person,
                tag=tag,
            )

        created += 1

    return created, skipped
