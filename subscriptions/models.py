from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class Plan(models.Model):
    """
    Subscription plan (monthly or yearly). price in USD (Decimal).
    """
    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    key = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIOD_CHOICES, default="monthly")
    stripe_price_id = models.CharField(max_length=200, blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("billing_period", "price")

    def __str__(self):
        return f"{self.name} ({self.price}) - {self.get_billing_period_display()}"


class Subscription(models.Model):
    """
    A user's subscription to a Plan (recurring).
    status: pending -> active -> past_due -> canceled
    """
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_CANCELED, "Canceled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    pending_approval = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("user", "plan")

    def active(self):
        return self.status == self.STATUS_ACTIVE and not self.pending_approval

    def __str__(self):
        return f"{self.user} → {self.plan.key} ({self.status})"


class CreatorSubscription(models.Model):
    """
    A subscriber paying a monthly fee to a creator (user).
    """
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_CANCELED = "canceled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_CANCELED, "Canceled"),
    ]

    subscriber = models.ForeignKey(User, on_delete=models.CASCADE, related_name="creator_subscriptions")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscribers")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    last_paid_at = models.DateTimeField(null=True, blank=True)
    pending_approval = models.BooleanField(default=False)

    class Meta:
        unique_together = ("subscriber", "creator")

    def is_active(self):
        return self.status == self.STATUS_ACTIVE and not self.pending_approval

    def __str__(self):
        return f"{self.subscriber.username} → {self.creator.username} (${self.amount})"


class PayoutRequest(models.Model):
    """Request to payout affiliate commissions."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payout_requests")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    external_reference = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Payout {self.id} - {self.user.username} (${self.amount})"