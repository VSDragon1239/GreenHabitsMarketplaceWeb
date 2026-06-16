import csv

from django import forms
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import User

from apps.accounts.models import Profile

ROLE_CHOICES = (
    ("Участники", "Участник"),
    ("Руководители", "Руководитель"),
    ("Контент-менеджеры", "Контент-менеджер"),
)


class UserUpdateForm(UserChangeForm):
    password = None
    role = forms.ChoiceField(choices=ROLE_CHOICES, label="Роль")

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "role"
        ]


# class ProfileAvatarForm(forms.ModelForm):
#     class Meta:
#         model = Profile
#         fields = ['avatar']
class ProfileAvatarForm(forms.ModelForm):
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500',
            'rows': 4}),
        required=False
    )

    class Meta:
        model = Profile
        fields = ['avatar', 'description', 'phone']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'hidden', 'id': 'avatar_input'}),
            # Скрытый input, нажатие на кастомную кнопку вызовет его
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
        }


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg text-base focus:outline-none focus:border-green-500'}),
        }
