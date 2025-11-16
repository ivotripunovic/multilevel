from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from .forms import RegisterForm, LoginForm
from affiliates.models import Profile  # integrate affiliates Profile
from affiliates import utils as aff_utils

@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Register view: supports ?ref=<referral_code> and POST field referral_code.
    On successful registration, attaches Profile.referred_by if referral matches.
    """
    initial = {}
    ref = request.GET.get("ref") or request.POST.get("referral_code") or request.POST.get("ref")
    if ref:
        initial["referral_code"] = ref

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()
            # Ensure Profile exists
            profile, _ = Profile.objects.get_or_create(user=user)
            # Link referrer if code provided
            code = form.cleaned_data.get("referral_code") or ref
            if code:
                try:
                    ref_profile = Profile.objects.get(referral_code=code)
                    profile.referred_by = ref_profile.user
                    profile.save()
                except Profile.DoesNotExist:
                    pass
            # log in and redirect
            login(request, user)
            return redirect("home")
    else:
        form = RegisterForm(initial=initial)
    return render(request, "accounts/register.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Simple login view using Django auth. Accepts next param.
    """
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            nxt = request.GET.get("next") or request.POST.get("next") or "home"
            return redirect(nxt)
    else:
        form = LoginForm(request)
    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")