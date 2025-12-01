from django.contrib import admin
from .models import Subscription, CreatorSubscription, Plan
from affiliates import utils as aff_utils
from payments.utils import record_payment, complete_payment


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "price", "billing_period", "active", "created_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "pending_approval", "created_at")
    actions = ["approve_payment"]

    @admin.action(description="Approve selected subscription payments")
    def approve_payment(self, request, queryset):
        """
        Admin action to mark subscription(s) as approved (funds received).
        This will set pending_approval=False and status active, and trigger commission distribution.
        """
        for sub in queryset:
            # create a record in payments or transactions as desired (example uses payments.utils)
            p = record_payment(
                company=None, amount=sub.plan.price, payer=sub.user, fee=0
            )
            complete_payment(p)
            aff_utils.distribute_commissions(sub.user, sub.plan.price)

        queryset.update(pending_approval=False, status=Subscription.STATUS_ACTIVE)


@admin.register(CreatorSubscription)
class CreatorSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("subscriber", "creator", "status", "created_at")
    actions = ["approve_payment"]

    @admin.action(description="Approve selected creator subscription payments")
    def approve_payment(self, request, queryset):
        """
        Admin action to mark creator subscription(s) as approved (funds received).
        This will set pending_approval=False and status active, and trigger commission distribution.
        """
        for sub in queryset:
            p = record_payment(
                company=None, amount=sub.monthly_fee, payer=sub.subscriber, fee=0
            )
            complete_payment(p)
            aff_utils.distribute_commissions(sub.subscriber, sub.monthly_fee)

        queryset.update(
            pending_approval=False, status=CreatorSubscription.STATUS_ACTIVE
        )
