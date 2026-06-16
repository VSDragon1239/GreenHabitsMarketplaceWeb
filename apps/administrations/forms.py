from django import forms
from django.contrib.auth.models import User, Group
from apps.marketplace.models import EcoTask




class AdminUserForm(forms.ModelForm):
    # Поля профиля
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3}))

    # Поле пароля (необязательное при редактировании)
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Оставьте пустым, если не меняете'})
    )

    # Роли (Группы)
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-input h-24'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_superuser': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Заполняем поля профиля при редактировании
            self.fields['phone'].initial = self.instance.profile.phone
            self.fields['description'].initial = self.instance.profile.description


class EcoTaskForm(forms.ModelForm):
    class Meta:
        model = EcoTask
        fields = ['title', 'description', 'reward', 'task_type', 'secret_code', 'is_active']
        widgets = {
            'title': forms.TextInput(
                attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none'}),
            'description': forms.Textarea(attrs={'rows': 4,
                                                 'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none'}),
            'reward': forms.NumberInput(
                attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none'}),
            'task_type': forms.Select(
                attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none'}),
            'secret_code': forms.TextInput(
                attrs={'class': 'w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-green-500 outline-none',
                       'placeholder': 'Оставьте пустым, если не требуется'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'w-5 h-5 text-green-600 rounded'}),
        }
