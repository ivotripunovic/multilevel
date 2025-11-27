import os
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from payments.gateways.registry import get_gateway
from .models import Plan, Subscription
from affiliates import utils as aff_utils
from payments.utils import record_payment, complete_payment

# create checkout session (generic)
def create_checkout_session_for_plan(request, plan_key):
    plan = get_object_or_404(Plan, key=plan_key, active=True)
    gateway = get_gateway()
    session = gateway.create_checkout_session(request, plan=plan, metadata={"plan_key": plan.key})
    return JsonResponse(session)


@csrf_exempt
def gateway_webhook(request):
    """
    Generic webhook endpoint: delegates parsing to selected gateway, then handles normalized events.
    """
    gateway = get_gateway()
    try:
        event_type, data = gateway.parse_webhook(request)
    except Exception:
        return HttpResponseForbidden()

    # handle common normalized events
    if event_type in ("checkout.session.completed", "checkout.session.completed.v1"):
        # create local pending subscription record (metadata may contain plan_key/user_id)
        user_id = data.get("client_reference_id") or data.get("metadata", {}).get("user_id")
        plan_key = data.get("metadata", {}).get("plan_key")
        if user_id and plan_key:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=int(user_id))
                plan = Plan.objects.get(key=plan_key)
                Subscription.objects.update_or_create(user=user, plan=plan, defaults={"status": Subscription.STATUS_PENDING})
            except Exception:
                pass

    if event_type in ("invoice.payment_succeeded", "invoice.payment_succeeded.v1", "payment_intent.succeeded"):
        # normalized amount expected in data['amount'] as Decimal
        amount = data.get("amount")
        if amount is None and "amount_paid" in data:
            try:
                amount = Decimal(str(data["amount_paid"])) / Decimal("100")
            except Exception:
                amount = Decimal("0.00")
        # map stripe sub id to local subscription if present
        sub_id = data.get("subscription")
        subs = Subscription.objects.filter(stripe_subscription_id=sub_id) if sub_id else Subscription.objects.none()
        if subs.exists():
            for s in subs:
                s.status = Subscription.STATUS_ACTIVE
                s.pending_approval = False
                s.current_period_start = timezone.now() if not s.current_period_start else s.current_period_start
                s.current_period_end = timezone.now()
                s.save()
                # record payment and run affiliate distribution
                p = record_payment(company=None, amount=amount or Decimal("0.00"), payer=s.user, fee=Decimal("0.00"))
                complete_payment(p)
                aff_utils.distribute_commissions(s.user, amount or Decimal("0.00"))
        # also try to create subscription by metadata/user mapping when sub not found
        if not subs.exists():
            user_id = data.get("client_reference_id") or data.get("metadata", {}).get("user_id")
            plan_key = data.get("metadata", {}).get("plan_key")
            if user_id and plan_key:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                try:
                    user = User.objects.get(id=int(user_id))
                    plan = Plan.objects.get(key=plan_key)
                    Subscription.objects.update_or_create(user=user, plan=plan, defaults={"status": Subscription.STATUS_ACTIVE, "pending_approval": False})
                    # record payment and distribute
                    p = record_payment(company=None, amount=amount or plan.price, payer=user, fee=Decimal("0.00"))
                    complete_payment(p)
                    aff_utils.distribute_commissions(user, amount or plan.price)
                except Exception:
                    pass

    # other event types can be handled similarly
    return HttpResponse(status=200)


@login_required
def cancel_subscription(request, subscription_id):
    """Cancel a user's subscription."""
    sub = get_object_or_404(Subscription, id=subscription_id, user=request.user)
    sub.status = Subscription.STATUS_CANCELED
    sub.save()
    messages.success(request, f"Subscription to {sub.plan.name} has been canceled.")
    return redirect("accounts-profile")


def checkout_success(request):
    """Handle successful checkout redirect."""
    messages.success(request, "Subscription created successfully! Awaiting payment confirmation.")
    return redirect("accounts-profile")


def checkout_cancel(request):
    """Handle canceled checkout."""
    messages.warning(request, "Subscription checkout was canceled.")
    return redirect("accounts-profile")