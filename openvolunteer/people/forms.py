from django import forms

from openvolunteer.orgs.models import Organization
from openvolunteer.orgs.permissions import user_can_manage_people
from openvolunteer.people.models import PersonOrganization
from openvolunteer.people.models import PersonTagging

from .models import Person
from .models import PersonTag


class PersonForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=PersonTag.objects.all(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    organizations = forms.ModelMultipleChoiceField(
        queryset=Organization.objects.all(),
        required=False,
        widget=forms.MultipleHiddenInput,
    )

    class Meta:
        model = Person
        fields = [
            "full_name",
            "discord",
            "email",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "postal_code",
            "attributes",
        ]
        widgets = {
            "attributes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "form-control",
                    "placeholder": '{"support_level": "strong"}',
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["tags"].queryset = PersonTag.objects.all()

        # Preselect existing tags when editing
        if self.instance.pk:
            self.initial["tags"] = self.instance.taggings.values_list(
                "tag_id",
                flat=True,
            )

        if self.user and self.user.is_authenticated:
            allowed_orgs = [
                org
                for org in Organization.objects.all()
                if user_can_manage_people(self.user, org)
            ]

            self.fields["organizations"].queryset = Organization.objects.filter(
                id__in=[org.id for org in allowed_orgs],
            )

        else:
            self.fields["organizations"].queryset = Organization.objects.none()

        # Preselect existing orgs (even if user can't edit them)
        if self.instance.pk:
            self.initial["organizations"] = self.instance.org_links.values_list(
                "org_id",
                flat=True,
            )

    # ruff: noqa: FBT002
    def save(self, commit=True):
        person = super().save(commit)

        if not commit:
            return person

        existing_tags = set(
            person.taggings.values_list("tag_id", flat=True),
        )
        submitted_tags = set(
            self.cleaned_data.get("tags", []).values_list("id", flat=True),
        )

        tags_to_add = submitted_tags - existing_tags
        tags_to_remove = existing_tags - submitted_tags

        if tags_to_remove:
            PersonTagging.objects.filter(
                person=person,
                tag_id__in=tags_to_remove,
            ).delete()

        if tags_to_add:
            PersonTagging.objects.bulk_create(
                [PersonTagging(person=person, tag_id=tag_id) for tag_id in tags_to_add],
            )

        existing_orgs = set(
            person.org_links.values_list("org_id", flat=True),
        )
        submitted_orgs = set(
            self.cleaned_data.get("organizations", []).values_list("id", flat=True),
        )

        allowed_orgs = set(
            self.fields["organizations"].queryset.values_list("id", flat=True),
        )

        # Only mutate orgs user is allowed to manage
        safe_add = (submitted_orgs - existing_orgs) & allowed_orgs
        safe_remove = (existing_orgs - submitted_orgs) & allowed_orgs

        if safe_remove:
            PersonOrganization.objects.filter(
                person=person,
                org_id__in=safe_remove,
            ).delete()

        if safe_add:
            PersonOrganization.objects.bulk_create(
                [
                    PersonOrganization(person=person, org_id=org_id)
                    for org_id in safe_add
                ],
            )

        return person


class PersonCSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        help_text="Upload a CSV file with people data",
    )


class PersonTagForm(forms.ModelForm):
    color = forms.CharField(widget=forms.TextInput(attrs={"type": "color"}))

    class Meta:
        model = PersonTag
        fields = ["name", "color"]
