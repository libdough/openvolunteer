from django import forms

from openvolunteer.people.models import Person
from openvolunteer.users.models import User

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


class AddUserToOrgForm(forms.Form):
    user_id = forms.IntegerField(widget=forms.HiddenInput)
    role = forms.ChoiceField(choices=OrgRole.choices, initial=OrgRole.VOLUNTEER)

    def clean_user_id(self):
        user_id = self.cleaned_data["user_id"]
        try:
            self.user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            msg = "Invalid user"
            raise forms.ValidationError(msg) from None
        return user_id


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
