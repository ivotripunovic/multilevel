from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Sum


from affiliates.models import Profile, Commission
from affiliates import utils as aff_utils
from subscriptions.models import Plan, Subscription
from subscriptions.models import CreatorSubscription

from .forms import RegisterForm, LoginForm
from django.contrib.auth import get_user_model

User = get_user_model()


@require_http_methods(["GET", "POST"])
def register_view(request):
    """
    Register view: supports ?ref=<referral_code> and POST field referral_code.
    On successful registration, attaches Profile.referred_by if referral matches.
    Preserves referral_code in form.initial on validation errors.
    """
    # determine referral code from GET or POST
    ref = (
        request.GET.get("ref")
        or request.POST.get("referral_code")
        or request.POST.get("ref")
    )
    initial = {}
    if ref:
        initial["referral_code"] = ref

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data.get("email", "")
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
            login(request, user)
            return redirect("home")
        else:
            # Preserve referral_code in form.initial so templates/tests can read it after validation errors
            try:
                form.initial = dict(form.initial) if form.initial is not None else {}
            except Exception:
                form.initial = {}
            # prefer posted value, fallback to ref
            posted_ref = request.POST.get("referral_code") or request.POST.get("ref")
            form.initial["referral_code"] = posted_ref or ref or ""
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
    """Display user profile with subscriptions, affiliate info, and commissions."""
    profile = Profile.objects.get(user=request.user)

    # Get subscription data
    active_subscriptions = Subscription.objects.filter(
        user=request.user, status=Subscription.STATUS_ACTIVE, pending_approval=False
    )
    pending_subscriptions = Subscription.objects.filter(
        user=request.user, status=Subscription.STATUS_PENDING
    )

    # Get available plans user is not subscribed to
    subscribed_plan_ids = Subscription.objects.filter(user=request.user).values_list(
        "plan_id"
    )
    available_plans = Plan.objects.filter(active=True).exclude(
        id__in=subscribed_plan_ids
    )

    # Get active creator subscriptions
    active_creator_subscriptions = CreatorSubscription.objects.filter(
        subscriber=request.user,
        status=CreatorSubscription.STATUS_ACTIVE,
        pending_approval=False,
    )

    # Get available creators (users with profiles, excluding current user and already subscribed)
    subscribed_creator_ids = active_creator_subscriptions.values_list("creator_id")
    available_creators = (
        User.objects.filter(profile__isnull=False)
        .exclude(id__in=subscribed_creator_ids)
        .exclude(id=request.user.id)
        .order_by("-date_joined")[:20]
    )

    # Affiliate data
    direct_referral_count = Profile.objects.filter(referred_by=request.user).count()
    all_downline = aff_utils.get_downline_users(request.user, max_levels=10)
    total_referral_count = len(all_downline)

    # Commission data
    pending_commissions = Commission.objects.filter(
        recipient=request.user, approved=False
    )
    pending_commissions_total = (
        pending_commissions.aggregate(total=Sum("amount"))["total"] or 0
    )

    approved_commissions = Commission.objects.filter(
        recipient=request.user, approved=True
    )
    approved_commissions_total = (
        approved_commissions.aggregate(total=Sum("amount"))["total"] or 0
    )

    # Build downline with levels
    downline = []
    for user, level in all_downline[:50]:
        downline.append({"user": user, "level": level})

    # Build affiliate link
    affiliate_link = request.build_absolute_uri(
        f"/accounts/register/?ref={profile.referral_code}"
    )

    context = {
        "profile": profile,
        "active_subscriptions": active_subscriptions,
        "pending_subscriptions": pending_subscriptions,
        "available_plans": available_plans,
        "active_creator_subscriptions": active_creator_subscriptions,
        "available_creators": available_creators,
        "direct_referral_count": direct_referral_count,
        "total_referral_count": total_referral_count,
        "downline": downline,
        "affiliate_link": affiliate_link,
        "pending_commissions": pending_commissions,
        "pending_commissions_total": pending_commissions_total,
        "approved_commissions": approved_commissions,
        "approved_commissions_total": approved_commissions_total,
    }
    return render(request, "accounts/profile.html", context)
