from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    referral_code = forms.CharField(max_length=64, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "password")