from django import forms
from .models import Mailing


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message']
        labels = {
            'start_time': 'Начало рассылки',
            'end_time': 'Окончание рассылки',
            'message': 'Сообщение',
            'recipients': 'Получатели'
        }
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }




