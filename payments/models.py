from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Company(models.Model):
    """
    Represents a merchant or company that receives payments.
    """
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="companies")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


class CompanyRevenue(models.Model):
    """
    Aggregate revenue record for a company (cached).
    Use compute_company_revenue to recalc if needed.
    """
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="revenue")
    total_revenue = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} revenue: {self.total_revenue}"


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="payments")
    payer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments_made")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="Gateway transaction id")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def net_amount(self):
        return (self.amount or Decimal("0.00")) - (self.fee or Decimal("0.00"))

    def __str__(self):
        return f"Payment {self.id} {self.company} {self.amount} {self.currency}"


class Transaction(models.Model):
    TYPE_CHARGE = "charge"
    TYPE_REFUND = "refund"
    TYPE_PAYOUT = "payout"

    TYPE_CHOICES = [
        (TYPE_CHARGE, "Charge"),
        (TYPE_REFUND, "Refund"),
        (TYPE_PAYOUT, "Payout"),
    ]

    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL, related_name="transactions")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="transactions")
    tx_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(default=timezone.now)
    external_reference = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def net_amount(self):
        return (self.amount or Decimal("0.00")) - (self.fee or Decimal("0.00"))

    def __str__(self):
        return f"Transaction {self.id} {self.tx_type} {self.amount}"