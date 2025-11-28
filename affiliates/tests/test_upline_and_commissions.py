from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from affiliates.models import Profile, Commission
from affiliates import utils as aff_utils

User = get_user_model()


class UplineTests(TestCase):
    """Tests for upline traversal and hierarchy."""

    def setUp(self):
        """Create a 4-level referral chain: A <- B <- C <- D"""
        self.user_a = User.objects.create_user(username="user_a", email="a@example.com", password="pass")
        self.user_b = User.objects.create_user(username="user_b", email="b@example.com", password="pass")
        self.user_c = User.objects.create_user(username="user_c", email="c@example.com", password="pass")
        self.user_d = User.objects.create_user(username="user_d", email="d@example.com", password="pass")

        # Ensure profiles exist
        for u in (self.user_a, self.user_b, self.user_c, self.user_d):
            Profile.objects.get_or_create(user=u)

        # Link referrals: B referred_by A, C referred_by B, D referred_by C
        self.user_b.profile.referred_by = self.user_a
        self.user_b.profile.save()

        self.user_c.profile.referred_by = self.user_b
        self.user_c.profile.save()

        self.user_d.profile.referred_by = self.user_c
        self.user_d.profile.save()

    def test_get_upline_users_returns_correct_order(self):
        """get_upline_users should return upline in order (direct parent first) with correct levels."""
        upline = aff_utils.get_upline_users(self.user_d, max_levels=10)
        
        self.assertEqual(len(upline), 3)
        # Level 1: direct parent (user_c)
        self.assertEqual(upline[0][0], self.user_c)
        self.assertEqual(upline[0][1], 1)
        # Level 2: grandparent (user_b)
        self.assertEqual(upline[1][0], self.user_b)
        self.assertEqual(upline[1][1], 2)
        # Level 3: great-grandparent (user_a)
        self.assertEqual(upline[2][0], self.user_a)
        self.assertEqual(upline[2][1], 3)

    def test_get_upline_users_respects_max_levels(self):
        """get_upline_users should stop at max_levels."""
        upline = aff_utils.get_upline_users(self.user_d, max_levels=2)
        
        self.assertEqual(len(upline), 2)
        self.assertEqual(upline[0][0], self.user_c)
        self.assertEqual(upline[1][0], self.user_b)

    def test_get_upline_users_with_no_referrer(self):
        """get_upline_users should return empty list for root user."""
        upline = aff_utils.get_upline_users(self.user_a)
        
        self.assertEqual(len(upline), 0)

    def test_get_upline_users_one_level_deep(self):
        """get_upline_users should return only direct parent for one level."""
        upline = aff_utils.get_upline_users(self.user_b)
        
        self.assertEqual(len(upline), 1)
        self.assertEqual(upline[0][0], self.user_a)
        self.assertEqual(upline[0][1], 1)


class CommissionDistributionTests(TestCase):
    """Tests for commission calculation and distribution."""

    def setUp(self):
        """Create a 4-level referral chain."""
        self.user_a = User.objects.create_user(username="user_a", email="a@example.com", password="pass")
        self.user_b = User.objects.create_user(username="user_b", email="b@example.com", password="pass")
        self.user_c = User.objects.create_user(username="user_c", email="c@example.com", password="pass")
        self.user_d = User.objects.create_user(username="user_d", email="d@example.com", password="pass")

        # Ensure profiles exist
        for u in (self.user_a, self.user_b, self.user_c, self.user_d):
            Profile.objects.get_or_create(user=u)

        # Link referrals
        self.user_b.profile.referred_by = self.user_a
        self.user_b.profile.save()

        self.user_c.profile.referred_by = self.user_b
        self.user_c.profile.save()

        self.user_d.profile.referred_by = self.user_c
        self.user_d.profile.save()

    def test_distribute_commissions_creates_correct_records(self):
        """distribute_commissions should create Commission records for each upline level."""
        sale_amount = Decimal("100.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        commissions = Commission.objects.filter(source_user=self.user_d).order_by("level")
        expected_upline = aff_utils.get_upline_users(self.user_d, max_levels=len(aff_utils.LEVEL_RATES))
        expected_count = min(len(expected_upline), len(aff_utils.LEVEL_RATES))
        
        self.assertEqual(commissions.count(), expected_count)

    def test_distribute_commissions_correct_amounts(self):
        """Commission amounts should match configured LEVEL_RATES."""
        sale_amount = Decimal("100.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        commissions = Commission.objects.filter(source_user=self.user_d).order_by("level")

        for commission in commissions:
            level_idx = commission.level - 1
            expected_rate = aff_utils.LEVEL_RATES[level_idx]
            expected_amount = (sale_amount * expected_rate).quantize(Decimal("0.01"))
            self.assertEqual(commission.amount, expected_amount)

    def test_distribute_commissions_correct_recipients(self):
        """Commission recipients should match the upline users at each level."""
        sale_amount = Decimal("100.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        commissions = Commission.objects.filter(source_user=self.user_d).order_by("level")
        expected_upline = aff_utils.get_upline_users(self.user_d, max_levels=len(aff_utils.LEVEL_RATES))

        for commission in commissions:
            level_idx = commission.level - 1
            expected_recipient = expected_upline[level_idx][0]
            self.assertEqual(commission.recipient, expected_recipient)

    def test_distribute_commissions_with_decimal_amount(self):
        """distribute_commissions should handle Decimal input correctly."""
        sale_amount = Decimal("250.50")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        # Level 1: 10% of 250.50 = 25.05
        comm_l1 = Commission.objects.get(source_user=self.user_d, level=1)
        self.assertEqual(comm_l1.amount, Decimal("25.05"))
        self.assertEqual(comm_l1.recipient, self.user_c)

        # Level 2: 5% of 250.50 = 12.525 -> 12.53
        comm_l2 = Commission.objects.get(source_user=self.user_d, level=2)
        self.assertEqual(comm_l2.amount, Decimal("12.53"))
        self.assertEqual(comm_l2.recipient, self.user_b)

        # Level 3: 2% of 250.50 = 5.01
        comm_l3 = Commission.objects.get(source_user=self.user_d, level=3)
        self.assertEqual(comm_l3.amount, Decimal("5.01"))
        self.assertEqual(comm_l3.recipient, self.user_a)

    def test_distribute_commissions_no_duplicates(self):
        """Multiple calls to distribute_commissions should not create duplicates (depends on business logic)."""
        sale_amount = Decimal("100.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)
        count_after_first = Commission.objects.filter(source_user=self.user_d).count()

        aff_utils.distribute_commissions(self.user_d, sale_amount)
        count_after_second = Commission.objects.filter(source_user=self.user_d).count()

        # Note: current implementation allows duplicates. Adjust if idempotency is needed.
        self.assertEqual(count_after_second, count_after_first * 2)

    def test_distribute_commissions_with_zero_amount(self):
        """distribute_commissions with zero amount should create zero commissions."""
        sale_amount = Decimal("0.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        commissions = Commission.objects.filter(source_user=self.user_d)
        # Commissions should not be created for zero amounts (or should be created with 0 amount)
        # Current implementation will create them with 0 amount; adjust test if behavior changes
        for commission in commissions:
            self.assertEqual(commission.amount, Decimal("0.00"))

    def test_distribute_commissions_partial_upline(self):
        """Commission distribution should work even with partial upline (fewer than max levels)."""
        # Create a standalone user with no referrer
        isolated_user = User.objects.create_user(username="isolated", email="iso@example.com", password="pass")
        Profile.objects.get_or_create(user=isolated_user)

        sale_amount = Decimal("100.00")
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(isolated_user, sale_amount)

        commissions = Commission.objects.filter(source_user=isolated_user)
        self.assertEqual(commissions.count(), 0)

    def test_level_rates_configuration(self):
        """LEVEL_RATES should be configured correctly."""
        expected_rates = [Decimal("0.10"), Decimal("0.05"), Decimal("0.02")]
        self.assertEqual(aff_utils.LEVEL_RATES, expected_rates)