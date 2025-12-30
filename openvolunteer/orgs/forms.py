from django import forms

from openvolunteer.people.models import Person
from openvolunteer.users.models import User

from .models import Membership
from .models import Organization
from .models import OrgRole


class OrganizationForm(forms.ModelForm):
    class Meta:
        model = Organization
        fields = ["name", "slug"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "slug": forms.TextInput(attrs={"class": "form-control"}),
        }


class MembershipRoleForm(forms.ModelForm):
    """
    Used to update an existing member's role.
    """

    class Meta:
        model = Membership
        fields = ["role"]
        widgets = {
            "role": forms.Select(
                choices=OrgRole.choices,
                attrs={"class": "form-select"},
            ),
        }


class AddMemberForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=OrgRole.choices, initial=OrgRole.VOLUNTEER)

    def clean_user_id(self):
        user_id = self.cleaned_data["user_id"]
        if not User.objects.filter(id=user_id).exists():
            msg = "Invalid user"
            raise forms.ValidationError(msg)
        return user_id


class UpdateMemberRoleForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["role"]


class AddPersonToOrgForm(forms.Form):
    person = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        label="Person",
    )

    def __init__(self, *args, org=None, **kwargs):
        super().__init__(*args, **kwargs)

        if org:
            self.fields["person"].queryset = Person.objects.exclude(
                org_links__org=org,
            ).order_by("full_name")
