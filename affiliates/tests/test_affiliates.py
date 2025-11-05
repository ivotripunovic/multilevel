from decimal import Decimal

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from affiliates.models import Profile, Commission
from affiliates import utils as aff_utils

User = get_user_model()


class AffiliateTests(TestCase):
    def setUp(self):
        # Create a chain: A <- B <- C <- D  (A is top upline, D is newest user)
        self.user_a = User.objects.create_user(username="user_a", email="a@example.com", password="pass")
        self.user_b = User.objects.create_user(username="user_b", email="b@example.com", password="pass")
        self.user_c = User.objects.create_user(username="user_c", email="c@example.com", password="pass")
        self.user_d = User.objects.create_user(username="user_d", email="d@example.com", password="pass")

        # Ensure profiles exist (in case you don't have a post_save signal)
        for u in (self.user_a, self.user_b, self.user_c, self.user_d):
            Profile.objects.get_or_create(user=u)

        # Link referrals: B referred_by A, C referred_by B, D referred_by C
        self.user_b.profile.referred_by = self.user_a
        self.user_b.profile.save()

        self.user_c.profile.referred_by = self.user_b
        self.user_c.profile.save()

        self.user_d.profile.referred_by = self.user_c
        self.user_d.profile.save()

    def test_get_upline_users(self):
        """
        get_upline_users should return the upline in order (direct parent first)
        and correct level numbers.
        """
        upline = aff_utils.get_upline_users(self.user_d, max_levels=10)
        # Expect: (user_c,1), (user_b,2), (user_a,3)
        self.assertEqual(len(upline), 3)
        self.assertEqual(upline[0][0], self.user_c)
        self.assertEqual(upline[0][1], 1)
        self.assertEqual(upline[1][0], self.user_b)
        self.assertEqual(upline[1][1], 2)
        self.assertEqual(upline[2][0], self.user_a)
        self.assertEqual(upline[2][1], 3)

    def test_distribute_commissions_creates_correct_records(self):
        """
        distribute_commissions should create Commission records for each upline
        according to aff_utils.LEVEL_RATES and use the correct levels/amounts.
        """
        sale_amount = Decimal("100.00")
        # Clear any existing commissions
        Commission.objects.all().delete()

        aff_utils.distribute_commissions(self.user_d, sale_amount)

        # Fetch commissions issued for this source
        commissions = Commission.objects.filter(source_user=self.user_d).order_by("level")
        # We expect one commission per configured rate (or per available upline)
        expected_upline = aff_utils.get_upline_users(self.user_d, max_levels=len(aff_utils.LEVEL_RATES))
        expected_count = min(len(expected_upline), len(aff_utils.LEVEL_RATES))
        self.assertEqual(commissions.count(), expected_count)

        for commission in commissions:
            level_idx = commission.level - 1
            expected_rate = aff_utils.LEVEL_RATES[level_idx]
            expected_amount = (sale_amount * expected_rate).quantize(Decimal("0.01"))
            self.assertEqual(commission.amount, expected_amount)
            # recipient should match expected upline for that level
            expected_recipient = expected_upline[level_idx][0]
            self.assertEqual(commission.recipient, expected_recipient)

    def test_register_via_referral_link_attaches_referred_by(self):
        """
        Posting to /register/?ref=<referral_code> should create a new user whose
        Profile.referred_by is set to the referrer user.
        - This test posts to the raw path /register/ (adjust if your project uses a different URL)
        """
        client = Client()

        # Create a referrer with a referral_code
        referrer = User.objects.create_user(username="referrer", email="ref@example.com", password="pass")
        # Ensure referrer's profile has a referral_code
        ref_profile, _ = Profile.objects.get_or_create(user=referrer)
        # Make sure there's a referral_code (some implementations default-create one)
        if not ref_profile.referral_code:
            import uuid
            ref_profile.referral_code = str(uuid.uuid4())[:32]
            ref_profile.save()

        referral_code = ref_profile.referral_code

        # Post registration form; adjust form fields if your registration form differs
        resp = client.post(f"/register/?ref={referral_code}", data={
            "username": "new_referred",
            "email": "new@referred.example",
            "password": "newpass123",
        })

        self.assertEqual(resp.status_code, 302, "Registration did not redirect as expected. Check your /register/ view.")

        # New user should exist and have profile.referred_by set to referrer
        new_user = User.objects.filter(username="new_referred").first()
        self.assertIsNotNone(new_user, "Registration did not create the new user. Ensure /register/ view exists and uses posted fields.")
        # Ensure profile exists
        new_profile = Profile.objects.get(user=new_user)
        self.assertEqual(new_profile.referred_by, referrer)