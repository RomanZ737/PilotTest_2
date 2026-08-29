from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser
from django import forms


from django import forms
from .models import CustomUser


class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'middle_name',
            'email', 'phone_number',
            'position', 'ac_type', 'groups',
        ]
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'middle_name': 'Отчество',
            'email': 'Email',
            'phone_number': 'Телефон',
            'position': 'Должность',
            'ac_type': 'Тип ВС',
            'groups': 'Группы',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите имя',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите фамилию',
            }),
            'middle_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите отчество (если есть)',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'example@domain.com',
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+7 999 123 45 67',
            }),
            'position': forms.Select(attrs={
                'class': 'form-select',
            }),
            'ac_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'groups': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 6,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        groups = cleaned_data.get('groups')
        if not groups:
            self.add_error('groups', 'Необходимо назначить хотя бы одну группу.')
        return cleaned_data



class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=False,
                                   help_text='Необязательное поле. Введите ваш номер телефона.')
    username = forms.CharField(max_length=50, required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'password1', 'password2')
        usable_password = None


    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not phone_number.isdigit():
            raise forms.ValidationError('Номер телефона должен содержать только цифры.')
        return phone_number



class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': 'Неверный логин или пароль. Попробуйте ещё раз.',
        'inactive': 'Ваш аккаунт заблокирован. Обратитесь к администратору.',
    }

    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = ''