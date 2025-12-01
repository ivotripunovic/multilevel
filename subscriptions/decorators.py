from functools import wraps
from django.shortcuts import redirect
from .models import Subscription


def subscription_required(plan_key, redirect_to="accounts-register"):
    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(redirect_to)
            if Subscription.objects.filter(
                user=request.user,
                plan__key=plan_key,
                status=Subscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists():
                return view_func(request, *args, **kwargs)
            return redirect(redirect_to)

        return _wrapped

    return _decorator


def creator_subscription_required(
    creator_user_field="creator", redirect_to="accounts-register"
):
    def _decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(redirect_to)
            creator_id = kwargs.get(creator_user_field) or request.GET.get("creator_id")
            if not creator_id:
                return redirect(redirect_to)
            from .models import CreatorSubscription

            if CreatorSubscription.objects.filter(
                subscriber=request.user,
                creator_id=creator_id,
                status=Subscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists():
                return view_func(request, *args, **kwargs)
            return redirect(redirect_to)

        return _wrapped

    return _decorator
