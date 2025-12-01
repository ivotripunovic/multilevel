from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    referral_code = forms.CharField(
        max_length=150,
        required=False,
        help_text="Optional referrer's username",
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "referral_code")


class LoginForm(AuthenticationForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)