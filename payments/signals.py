from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Payment, Transaction, CompanyRevenue


@receiver(post_save, sender=Payment)
def on_payment_saved(sender, instance: Payment, created, **kwargs):
    """
    When a Payment becomes completed, create a Transaction and update company revenue.
    If status changes to refunded, create a refund transaction and adjust revenue.
    """
    # Only act on status changes to completed/refunded
    if instance.status == Payment.STATUS_COMPLETED:
        # create charge transaction if not already created for this payment
        if not instance.transactions.filter(tx_type=Transaction.TYPE_CHARGE).exists():
            Transaction.objects.create(
                payment=instance,
                company=instance.company,
                tx_type=Transaction.TYPE_CHARGE,
                amount=instance.amount,
                fee=instance.fee,
                external_reference=instance.external_id,
            )
        # update or create CompanyRevenue
        rev, _ = CompanyRevenue.objects.get_or_create(company=instance.company)
        # add net amount
        rev.total_revenue = (rev.total_revenue or Decimal("0.00")) + instance.net_amount
        rev.save()

    if instance.status == Payment.STATUS_REFUNDED:
        # create refund tx
        if not instance.transactions.filter(tx_type=Transaction.TYPE_REFUND).exists():
            Transaction.objects.create(
                payment=instance,
                company=instance.company,
                tx_type=Transaction.TYPE_REFUND,
                amount=instance.amount,
                fee=instance.fee,
                external_reference=instance.external_id,
            )
        # subtract net amount from company revenue (do not go negative here policy-dependent)
        rev, _ = CompanyRevenue.objects.get_or_create(company=instance.company)
        rev.total_revenue = (rev.total_revenue or Decimal("0.00")) - instance.net_amount
        if rev.total_revenue < Decimal("0.00"):
            rev.total_revenue = Decimal("0.00")
        rev.save()