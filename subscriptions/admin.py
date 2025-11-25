from django.contrib import admin
from .models import Subscription, CreatorSubscription, Plan

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "pending_approval", "created_at")
    actions = ["approve_payment"]

    def approve_payment(self, request, queryset):
        """
        Admin action to mark subscription(s) as approved (funds received).
        This will set pending_approval=False and status active, and trigger commission distribution.
        """
        from affiliates import utils as aff_utils
        for sub in queryset:
            sub.pending_approval = False
            sub.status = Subscription.STATUS_ACTIVE
            sub.save()
            # create a record in payments or transactions as desired (example uses payments.utils)
            from payments.utils import record_payment, complete_payment
            p = record_payment(company=None, amount=sub.plan.price, payer=sub.user, fee=0)
            complete_payment(p)
            aff_utils.distribute_commissions(sub.user, sub.plan.price)
    approve_payment.short_description = "Approve selected subscription payments"