from django import forms

from .models import Person
from .models import PersonTag


class PersonForm(forms.ModelForm):
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


class PersonTagForm(forms.ModelForm):
    color = forms.CharField(widget=forms.TextInput(attrs={"type": "color"}))

    class Meta:
        model = PersonTag
        fields = ["name", "color"]
