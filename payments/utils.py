from decimal import Decimal, ROUND_HALF_UP
import requests, os, time
from django.utils import timezone
from django.db import transaction as db_transaction

from .models import Payment, Transaction, CompanyRevenue


RATES_CACHE_TTL = 60 * 60  # 1 hour
_rates_cache = {"ts": 0, "base": "USD", "rates": {}}


def fetch_rates(base="USD"):
    # Minimal fetch from exchangerate.host (no API key) — replace with your provider.
    now = time.time()
    if _rates_cache["ts"] + RATES_CACHE_TTL > now and _rates_cache["base"] == base:
        return _rates_cache["rates"]
    url = f"https://api.exchangerate.host/latest?base={base}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    rates = data.get("rates", {})
    _rates_cache.update({"ts": now, "base": base, "rates": rates})
    return rates


def convert(amount: Decimal, from_currency: str, to_currency: str, quantize_exp=Decimal("0.01")) -> dict:
    """
    Convert Decimal amount from from_currency to to_currency.
    Returns dict with converted_amount (Decimal), rate (Decimal), ts (datetime).
    """
    if from_currency == to_currency:
        return {"converted": amount.quantize(quantize_exp, rounding=ROUND_HALF_UP), "rate": Decimal("1"), "ts": timezone.now()}
    rates = fetch_rates(base=from_currency)
    rate = Decimal(str(rates.get(to_currency)))
    converted = (amount * rate).quantize(quantize_exp, rounding=ROUND_HALF_UP)
    return {"converted": converted, "rate": rate, "ts": timezone.now()}


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