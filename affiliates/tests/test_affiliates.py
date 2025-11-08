from decimal import Decimal
import uuid

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

    def test_register_get_prefills_referral_code(self):
        """
        GET /register/?ref=<referral_code> should return 200 and the registration
        form should have the referral_code pre-filled in form.initial or field value.
        """
        client = Client()
        referrer = User.objects.create_user(username="ref_get", email="refget@example.com", password="pass")
        ref_profile, _ = Profile.objects.get_or_create(user=referrer)
        if not ref_profile.referral_code:
            ref_profile.referral_code = str(uuid.uuid4())[:32]
            ref_profile.save()
        referral_code = ref_profile.referral_code

        resp = client.get(f"/register/?ref={referral_code}")
        self.assertEqual(resp.status_code, 200, "GET /register/ did not return 200. Ensure the view handles GET and uses the 'ref' query param.")

        # Check form in context and initial value
        form = resp.context.get("form") if resp.context else None
        self.assertIsNotNone(form, "Response context has no 'form'. Ensure the register view passes 'form' to the template.")
        # prefer initial, fall back to bound field value if present
        initial_code = form.initial.get("referral_code") if hasattr(form, "initial") else None
        field_value = None
        try:
            field_value = form["referral_code"].value()
        except Exception:
            field_value = None

        self.assertTrue(initial_code == referral_code or field_value == referral_code,
                        "Referral code was not prefilled in the registration form (checked form.initial and form field value).")

    def test_register_get_returns_200_without_ref(self):
        """
        GET /register/ without ref param should return 200 and include a form in context.
        """
        client = Client()
        resp = client.get("/register/")
        self.assertEqual(resp.status_code, 200, "GET /register/ without ref did not return 200.")
        form = resp.context.get("form") if resp.context else None
        self.assertIsNotNone(form, "Response context has no 'form' for GET /register/.")

    def test_register_via_referral_link_attaches_referred_by(self):
        """
        Posting to /register/?ref=<referral_code> should create a new user whose
        Profile.referred_by is set to the referrer user.
        """
        client = Client()

        # Create a referrer with a referral_code
        referrer = User.objects.create_user(username="referrer", email="ref@example.com", password="pass")
        # Ensure referrer's profile has a referral_code
        ref_profile, _ = Profile.objects.get_or_create(user=referrer)
        # Make sure there's a referral_code (some implementations default-create one)
        if not ref_profile.referral_code:
            ref_profile.referral_code = str(uuid.uuid4())[:32]
            ref_profile.save()

        referral_code = ref_profile.referral_code

        # Post registration form; adjust form fields if your registration form differs
        resp = client.post(f"/register/?ref={referral_code}", data={
            "username": "new_referred",
            "email": "new@referred.example",
            "password": "newpass123",
        })

        # Accept either successful redirect or successful render; ensure user created
        self.assertIn(resp.status_code, (200, 302), f"Unexpected status code {resp.status_code} from POST /register/. Response body: {getattr(resp, 'content', b'')[:200]!r}")

        # New user should exist and have profile.referred_by set to referrer
        new_user = User.objects.filter(username="new_referred").first()
        self.assertIsNotNone(new_user, f"Registration did not create the new user. Response status: {resp.status_code}. Response body: {getattr(resp, 'content', b'')[:400]!r}")
        # Ensure profile exists
        new_profile = Profile.objects.get(user=new_user)
        self.assertEqual(new_profile.referred_by, referrer)