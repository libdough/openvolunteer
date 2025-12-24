from django.db import transaction

from .models import Person
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
