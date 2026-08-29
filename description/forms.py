from django import forms
from .models import DescriptionPage


class DescriptionPageForm(forms.ModelForm):
    class Meta:
        model = DescriptionPage
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20,}),
        }