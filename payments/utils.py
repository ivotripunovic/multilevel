from decimal import Decimal
from django.db import transaction as db_transaction

from .models import Payment, Transaction, CompanyRevenue


def record_payment(company, amount, payer=None, currency="USD", fee=Decimal("0.00"), external_id=None, metadata=None):
    """
    Create Payment in pending state. Returns Payment instance.
    """
    p = Payment.objects.create(
        company=company,
        payer=payer,
        amount=Decimal(amount),
        currency=currency,
        fee=Decimal(fee),
        external_id=external_id,
        metadata=metadata or {},
        status=Payment.STATUS_PENDING,
    )
    return p


def complete_payment(payment: Payment, external_id=None):
    """
    Mark payment completed and save. Signal will create Transaction and update revenue.
    """
    if external_id:
        payment.external_id = external_id
    payment.status = Payment.STATUS_COMPLETED
    payment.save()
    return payment


def refund_payment(payment: Payment, external_ref=None):
    """
    Mark payment refunded. Signal will create refund transaction & adjust revenue.
    """
    payment.status = Payment.STATUS_REFUNDED
    if external_ref:
        payment.external_id = external_ref
    payment.save()
    return payment


def compute_company_revenue(company):
    """
    Recompute revenue from transactions and update CompanyRevenue (idempotent).
    """
    txs = Transaction.objects.filter(company=company)
    total = Decimal("0.00")
    for tx in txs:
        if tx.tx_type == Transaction.TYPE_CHARGE:
            total += tx.net_amount
        elif tx.tx_type == Transaction.TYPE_REFUND:
            total -= tx.net_amount
        elif tx.tx_type == Transaction.TYPE_PAYOUT:
            total -= tx.net_amount
    rev, _ = CompanyRevenue.objects.get_or_create(company=company)
    rev.total_revenue = max(total, Decimal("0.00"))
    rev.save()
    return rev