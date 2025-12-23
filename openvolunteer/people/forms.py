from django import forms

from .models import Person
from .models import PersonTag


class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        fields = [
            "full_name",
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
            "attributes": forms.JSONField(
                widget=forms.Textarea(attrs={"rows": 3}),
                required=False,
            ),
        }


class PersonTagForm(forms.ModelForm):
    color = forms.CharField(widget=forms.TextInput(attrs={"type": "color"}))

    class Meta:
        model = PersonTag
        fields = ["name", "color"]
