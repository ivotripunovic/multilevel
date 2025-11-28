import uuid

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from affiliates.models import Profile

User = get_user_model()


class RegistrationViaReferralLinkTests(TestCase):
    """Tests for user registration through referral links."""

    def setUp(self):
        self.client = Client()
        # Create a referrer user
        self.referrer = User.objects.create_user(
            username="referrer_user",
            email="referrer@example.com",
            password="pass123"
        )
        # Ensure profile exists and has referral code
        self.referrer_profile, _ = Profile.objects.get_or_create(user=self.referrer)
        if not self.referrer_profile.referral_code:
            self.referrer_profile.referral_code = str(uuid.uuid4())[:32]
            self.referrer_profile.save()

    def test_register_get_with_ref_prefills_referral_code(self):
        """GET /accounts/register/?ref=<code> should prefill referral_code in form."""
        url = f"{reverse('accounts-register')}?ref={self.referrer_profile.referral_code}"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        form = response.context.get("form")
        self.assertIsNotNone(form)
        # Check if referral_code is in initial or form data
        initial_code = form.initial.get("referral_code") if hasattr(form, "initial") else None
        self.assertEqual(initial_code, self.referrer_profile.referral_code)

    def test_register_get_without_ref_returns_empty_form(self):
        """GET /accounts/register/ without ref should return form with empty referral_code."""
        url = reverse("accounts-register")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        form = response.context.get("form")
        self.assertIsNotNone(form)

    def test_register_post_with_valid_ref_attaches_referred_by(self):
        """POST /accounts/register/?ref=<code> should link new user to referrer."""
        url = f"{reverse('accounts-register')}?ref={self.referrer_profile.referral_code}"
        
        response = self.client.post(url, data={
            "username": "new_user",
            "email": "new@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": self.referrer_profile.referral_code,
        }, follow=True)

        # User should be created
        new_user = User.objects.filter(username="new_user").first()
        self.assertIsNotNone(new_user, "New user was not created")

        # Profile should exist and be linked to referrer
        new_profile = Profile.objects.get(user=new_user)
        self.assertEqual(new_profile.referred_by, self.referrer)

    def test_register_post_with_invalid_ref_ignores_referral(self):
        """POST with invalid referral_code should still create user (but without referrer link)."""
        url = reverse("accounts-register")
        
        response = self.client.post(url, data={
            "username": "unlinked_user",
            "email": "unlinked@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": "nonexistent_code_12345",
        }, follow=True)

        # User should still be created
        unlinked_user = User.objects.filter(username="unlinked_user").first()
        self.assertIsNotNone(unlinked_user)

        # Profile should exist but referred_by should be None
        unlinked_profile = Profile.objects.get(user=unlinked_user)
        self.assertIsNone(unlinked_profile.referred_by)

    def test_register_post_logs_in_user_on_success(self):
        """Successful registration should log in the user and redirect."""
        url = reverse("accounts-register")
        
        response = self.client.post(url, data={
            "username": "auto_login_user",
            "email": "autologin@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": "",
        }, follow=True)

        # User should be authenticated in session
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.username, "auto_login_user")

    def test_register_multiple_levels_of_referrals(self):
        """Create a chain of referrals: A -> B -> C and verify hierarchy."""
        # Create user A (referrer)
        user_a = User.objects.create_user(username="user_a_ref", email="a_ref@example.com", password="pass")
        profile_a, _ = Profile.objects.get_or_create(user=user_a)
        if not profile_a.referral_code:
            profile_a.referral_code = str(uuid.uuid4())[:32]
            profile_a.save()

        # Register user B via A's referral link
        url = f"{reverse('accounts-register')}?ref={profile_a.referral_code}"
        response = self.client.post(url, data={
            "username": "user_b_ref",
            "email": "b_ref@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": profile_a.referral_code,
        }, follow=True)

        user_b = User.objects.get(username="user_b_ref")
        profile_b = Profile.objects.get(user=user_b)
        self.assertEqual(profile_b.referred_by, user_a)

        # Register user C via B's referral link
        if not profile_b.referral_code:
            profile_b.referral_code = str(uuid.uuid4())[:32]
            profile_b.save()

        url = f"{reverse('accounts-register')}?ref={profile_b.referral_code}"
        response = self.client.post(url, data={
            "username": "user_c_ref",
            "email": "c_ref@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": profile_b.referral_code,
        }, follow=True)

        user_c = User.objects.get(username="user_c_ref")
        profile_c = Profile.objects.get(user=user_c)
        self.assertEqual(profile_c.referred_by, user_b)

        # Verify the chain
        self.assertEqual(profile_b.referred_by, user_a)
        self.assertEqual(profile_c.referred_by, user_b)

    def test_register_with_duplicate_username_shows_error(self):
        """Attempting to register with existing username should fail with error."""
        existing_user = User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="pass"
        )

        url = reverse("accounts-register")
        response = self.client.post(url, data={
            "username": "existing",
            "email": "new@example.com",
            "password1": "ComplexPass123!",
            "password2": "ComplexPass123!",
            "referral_code": "",
        })

        # Should not redirect on error; form should have errors
        self.assertEqual(response.status_code, 200)
        form = response.context.get("form")
        self.assertTrue(form.errors)

    def test_register_with_mismatched_passwords_shows_error(self):
        """Mismatched password fields should show validation error."""
        url = reverse("accounts-register")
        response = self.client.post(url, data={
            "username": "mismatch_user",
            "email": "mismatch@example.com",
            "password1": "ComplexPass123!",
            "password2": "DifferentPass123!",
            "referral_code": "",
        })

        self.assertEqual(response.status_code, 200)
        form = response.context.get("form")
        self.assertTrue(form.errors)

    def test_register_preserves_ref_in_form_on_validation_error(self):
        """Referral code should be preserved in form after validation error."""
        url = f"{reverse('accounts-register')}?ref={self.referrer_profile.referral_code}"
        
        # Submit with mismatched passwords
        response = self.client.post(url, data={
            "username": "error_user",
            "email": "error@example.com",
            "password1": "ComplexPass123!",
            "password2": "DifferentPass123!",
            "referral_code": self.referrer_profile.referral_code,
        })

        self.assertEqual(response.status_code, 200)
        form = response.context.get("form")
        self.assertTrue(form.errors)
        # Referral code should still be in the form's initial or field value
        initial_code = form.initial.get("referral_code")
        self.assertEqual(initial_code, self.referrer_profile.referral_code)