from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegistrationForm
from .models import Profile
from .utils import distribute_commissions

def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.save()
            # link referrer if provided
            code = form.cleaned_data.get("referral_code") or request.GET.get("ref")
            if code:
                try:
                    ref_profile = Profile.objects.get(referral_code=code)
                    user.profile.referred_by = ref_profile.user
                    user.profile.save()
                except Profile.DoesNotExist:
                    pass
            # optional: give commission for signup (or for purchase event separately)
            # distribute_commissions(user, amount=Decimal('...'))
            login(request, user)
            return redirect("home")
    else:
        form = RegistrationForm(initial={"referral_code": request.GET.get("ref", "")})
    return render(request, "affiliates/register.html", {"form": form})
