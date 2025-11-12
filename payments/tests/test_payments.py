from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from payments.models import Company, Payment, Transaction, CompanyRevenue
from payments.utils import record_payment, complete_payment, refund_payment, compute_company_revenue

User = get_user_model()


class PaymentsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="merchant_owner", password="pass")
        self.company = Company.objects.create(name="TestCo", owner=self.user)

    def test_record_and_complete_payment_creates_transaction_and_updates_revenue(self):
        p = record_payment(company=self.company, amount="120.00", payer=None, fee="2.50")
        self.assertEqual(p.status, Payment.STATUS_PENDING)
        complete_payment(p)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.STATUS_COMPLETED)

        tx = Transaction.objects.filter(payment=p, tx_type=Transaction.TYPE_CHARGE).first()
        self.assertIsNotNone(tx)
        # net amount should be amount - fee
        self.assertEqual(tx.net_amount, Decimal("117.50"))

        rev = CompanyRevenue.objects.get(company=self.company)
        self.assertEqual(rev.total_revenue, Decimal("117.50"))

    def test_refund_adjusts_revenue_and_creates_refund_tx(self):
        p = record_payment(company=self.company, amount="50.00", fee="0.50")
        complete_payment(p)
        refund_payment(p)
        p.refresh_from_db()
        self.assertEqual(p.status, Payment.STATUS_REFUNDED)

        refund_tx = Transaction.objects.filter(payment=p, tx_type=Transaction.TYPE_REFUND).first()
        self.assertIsNotNone(refund_tx)

        rev = CompanyRevenue.objects.get(company=self.company)
        # After refund revenue should be zero (we reset negative to 0)
        self.assertEqual(rev.total_revenue, Decimal("0.00"))

    def test_compute_company_revenue_recalculates_from_transactions(self):
        p1 = record_payment(company=self.company, amount="100.00", fee="1.00")
        complete_payment(p1)
        p2 = record_payment(company=self.company, amount="30.00", fee="0.50")
        complete_payment(p2)

        # Now compute revenue from transactions
        rev = compute_company_revenue(self.company)
        expected = (Decimal("100.00") - Decimal("1.00")) + (Decimal("30.00") - Decimal("0.50"))
        self.assertEqual(rev.total_revenue, expected)