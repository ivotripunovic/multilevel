import os
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.shortcuts import render

from affiliates.models import Profile
from affiliates import utils as aff_utils

from .forms import RegisterForm, LoginForm

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


@login_required
def profile_view(request):
    """
    Show the current user's profile info, an affiliate registration link,
    and the user's downline (all referred users) up to 3 levels deep.
    """
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    # ensure there's a referral_code
    if not profile.referral_code:
        import uuid
        profile.referral_code = str(uuid.uuid4())[:32]
        profile.save()

    # Build absolute affiliate registration link
    register_path = reverse("accounts-register")
    
    # Check if running in GitHub Codespace
    if 'CODESPACE_NAME' in os.environ:
        codespace_name = os.environ.get('CODESPACE_NAME')
        forwarding_domain = os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'preview.app.github.dev')
        base_url = f"https://{codespace_name}-8000.{forwarding_domain}"
        affiliate_link = f"{base_url}{register_path}?ref={profile.referral_code}"
    else:
        # Fallback to request.build_absolute_uri for local dev
        affiliate_link = request.build_absolute_uri(f"{register_path}?ref={profile.referral_code}")

    # get downline limited to 3 levels
    raw_downline = aff_utils.get_downline_users(user, max_levels=3)

    downline = [{"user": u, "level": lvl} for (u, lvl) in raw_downline]

    context = {
        "user": user,
        "profile": profile,
        "affiliate_link": affiliate_link,
        "downline": downline,
        "direct_referral_count": Profile.objects.filter(referred_by=user).count(),
        "total_referral_count": len(downline),
    }
    return render(request, "accounts/profile.html", context)