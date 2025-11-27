from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from subscriptions.models import Plan, Subscription, CreatorSubscription
from affiliates.models import Profile, Commission

User = get_user_model()


class PlanModelTests(TestCase):
    """Tests for Plan model."""

    def setUp(self):
        self.plan = Plan.objects.create(
            key="pro",
            name="Pro Plan",
            price=Decimal("9.99"),
            stripe_price_id="price_pro_stripe_id",
            active=True,
        )

    def test_plan_creation(self):
        self.assertEqual(self.plan.key, "pro")
        self.assertEqual(self.plan.price, Decimal("9.99"))
        self.assertTrue(self.plan.active)

    def test_plan_str(self):
        self.assertEqual(str(self.plan), "Pro Plan (9.99)")


class MonthlySubscriptionTests(TestCase):
    """Tests for monthly Plan subscriptions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="subscriber",
            email="sub@example.com",
            password="pass123"
        )
        self.plan = Plan.objects.create(
            key="monthly_pro",
            name="Monthly Pro",
            price=Decimal("19.99"),
            active=True,
        )

    def test_subscription_creation(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
        )
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.plan, self.plan)
        self.assertEqual(sub.status, Subscription.STATUS_PENDING)
        self.assertFalse(sub.pending_approval)

    def test_subscription_active_status(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            pending_approval=False,
        )
        self.assertTrue(sub.active())

    def test_subscription_not_active_with_pending_approval(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            pending_approval=True,
        )
        self.assertFalse(sub.active())

    def test_subscription_unique_constraint(self):
        """User can only have one subscription per plan."""
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        with self.assertRaises(Exception):
            Subscription.objects.create(
                user=self.user,
                plan=self.plan,
                status=Subscription.STATUS_PENDING,
            )

    def test_subscription_str(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        self.assertIn(str(self.user), str(sub))
        self.assertIn(self.plan.key, str(sub))

    def test_subscription_period_dates(self):
        now = timezone.now()
        end = now + timedelta(days=30)
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            current_period_start=now,
            current_period_end=end,
        )
        self.assertEqual(sub.current_period_start, now)
        self.assertEqual(sub.current_period_end, end)


class CreatorSubscriptionTests(TestCase):
    """Tests for user-generated content (creator) subscriptions."""

    def setUp(self):
        self.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass123"
        )
        self.subscriber = User.objects.create_user(
            username="subscriber",
            email="subscriber@example.com",
            password="pass123"
        )

    def test_creator_subscription_creation(self):
        csub = CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("4.99"),
            status=CreatorSubscription.STATUS_ACTIVE,
        )
        self.assertEqual(csub.subscriber, self.subscriber)
        self.assertEqual(csub.creator, self.creator)
        self.assertEqual(csub.amount, Decimal("4.99"))
        self.assertTrue(csub.is_active())

    def test_creator_subscription_not_active_with_pending_approval(self):
        csub = CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("4.99"),
            status=CreatorSubscription.STATUS_ACTIVE,
            pending_approval=True,
        )
        self.assertFalse(csub.is_active())

    def test_creator_subscription_unique_constraint(self):
        """Subscriber can only have one subscription per creator."""
        CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("4.99"),
        )
        with self.assertRaises(Exception):
            CreatorSubscription.objects.create(
                subscriber=self.subscriber,
                creator=self.creator,
                amount=Decimal("5.99"),
            )

    def test_creator_subscription_last_paid_at(self):
        now = timezone.now()
        csub = CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("4.99"),
            last_paid_at=now,
        )
        self.assertEqual(csub.last_paid_at, now)

    def test_creator_subscription_str(self):
        csub = CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("4.99"),
        )
        # Should contain subscriber and creator usernames
        str_rep = str(csub)
        self.assertIn(self.subscriber.username, str_rep)
        self.assertIn(self.creator.username, str_rep)


class SubscriptionWorkflowTests(TestCase):
    """Tests for subscription workflows: creation, approval, activation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user_workflow",
            email="workflow@example.com",
            password="pass123"
        )
        # Ensure user has a profile for affiliate tracking
        Profile.objects.get_or_create(user=self.user)

        self.plan = Plan.objects.create(
            key="workflow_plan",
            name="Workflow Plan",
            price=Decimal("9.99"),
            active=True,
        )

    def test_subscription_pending_to_active_workflow(self):
        """Test workflow: pending -> admin approval -> active."""
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
            pending_approval=True,
        )
        self.assertEqual(sub.status, Subscription.STATUS_PENDING)
        self.assertTrue(sub.pending_approval)
        self.assertFalse(sub.active())

        # Admin approves payment
        sub.pending_approval = False
        sub.status = Subscription.STATUS_ACTIVE
        sub.save()

        self.assertTrue(sub.active())

    def test_subscription_cancellation_workflow(self):
        """Test canceling an active subscription."""
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            pending_approval=False,
        )
        self.assertTrue(sub.active())

        # Cancel subscription
        sub.status = Subscription.STATUS_CANCELED
        sub.save()

        self.assertFalse(sub.active())
        self.assertEqual(sub.status, Subscription.STATUS_CANCELED)

    def test_subscription_past_due_workflow(self):
        """Test marking subscription as past due."""
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
        )
        # Payment fails, mark as past due
        sub.status = Subscription.STATUS_PAST_DUE
        sub.save()

        self.assertFalse(sub.active())
        self.assertEqual(sub.status, Subscription.STATUS_PAST_DUE)


class CreatorSubscriptionWithAffiliatesTests(TestCase):
    """Tests for creator subscriptions with affiliate commission distribution."""

    def setUp(self):
        # Create referral chain: affiliate -> subscriber -> creator
        self.creator = User.objects.create_user(
            username="creator_aff",
            email="creator_aff@example.com",
            password="pass123"
        )
        self.subscriber = User.objects.create_user(
            username="subscriber_aff",
            email="subscriber_aff@example.com",
            password="pass123"
        )
        self.affiliate = User.objects.create_user(
            username="affiliate_aff",
            email="affiliate_aff@example.com",
            password="pass123"
        )

        # Create profiles
        Profile.objects.get_or_create(user=self.creator)
        Profile.objects.get_or_create(user=self.affiliate)
        
        # Create subscriber profile and explicitly set referred_by
        subscriber_prof, _ = Profile.objects.get_or_create(user=self.subscriber)
        subscriber_prof.referred_by = self.affiliate
        subscriber_prof.save()
        
        # Refresh from DB to ensure relationship is loaded
        self.subscriber_profile = Profile.objects.select_related("referred_by").get(user=self.subscriber)
        self.affiliate_profile = Profile.objects.select_related("referred_by").get(user=self.affiliate)

    def test_creator_subscription_with_affiliate_commissions(self):
        """
        When a subscriber pays a creator and gets approved,
        commissions should distribute to the subscriber's upline (affiliate).
        """
        # Debug: verify the relationship exists in DB
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # Verify the upline is set up correctly
        from affiliates import utils as aff_utils
        from affiliates.models import Commission
        
        upline = aff_utils.get_upline_users(self.subscriber)
        self.assertGreater(len(upline), 0, f"Upline not set up. subscriber_profile.referred_by={self.subscriber_profile.referred_by}, upline={upline}")
        
        csub = CreatorSubscription.objects.create(
            subscriber=self.subscriber,
            creator=self.creator,
            amount=Decimal("10.00"),
            status=CreatorSubscription.STATUS_ACTIVE,
            pending_approval=False,
        )

        # Simulate admin approval and commission distribution
        created = aff_utils.distribute_commissions(self.subscriber, Decimal("10.00"))
        self.assertGreater(created, 0, "distribute_commissions returned 0 created commissions")

        # Check that commissions were created
        commissions = Commission.objects.filter(source_user=self.subscriber)
        self.assertGreater(commissions.count(), 0, "No commissions created for subscriber")

        # Affiliate (level 1) should receive 10% of 10.00 = 1.00
        level_1_commission = commissions.filter(level=1).first()
        self.assertIsNotNone(level_1_commission, "Level 1 commission not found")
        self.assertEqual(level_1_commission.recipient, self.affiliate)
        self.assertEqual(level_1_commission.amount, Decimal("1.00"))


class SubscriptionContentGatingTests(TestCase):
    """Tests for content access gating based on subscriptions."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="content_user",
            email="content@example.com",
            password="pass123"
        )
        self.creator = User.objects.create_user(
            username="content_creator",
            email="content_creator@example.com",
            password="pass123"
        )
        self.plan = Plan.objects.create(
            key="content_plan",
            name="Content Plan",
            price=Decimal("9.99"),
        )

    def test_user_with_active_subscription_can_access(self):
        """User with active subscription should be able to access gated content."""
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_ACTIVE,
            pending_approval=False,
        )
        # Check if subscription exists and is active
        self.assertTrue(
            Subscription.objects.filter(
                user=self.user,
                plan__key="content_plan",
                status=Subscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists()
        )

    def test_user_without_subscription_cannot_access(self):
        """User without subscription should not be able to access gated content."""
        self.assertFalse(
            Subscription.objects.filter(
                user=self.user,
                plan__key="content_plan",
                status=Subscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists()
        )

    def test_user_with_pending_subscription_cannot_access(self):
        """User with pending subscription should not be able to access gated content."""
        Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=Subscription.STATUS_PENDING,
            pending_approval=True,
        )
        self.assertFalse(
            Subscription.objects.filter(
                user=self.user,
                plan__key="content_plan",
                status=Subscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists()
        )

    def test_creator_subscription_gating(self):
        """User subscribed to creator should access creator content."""
        csub = CreatorSubscription.objects.create(
            subscriber=self.user,
            creator=self.creator,
            amount=Decimal("4.99"),
            status=CreatorSubscription.STATUS_ACTIVE,
            pending_approval=False,
        )
        self.assertTrue(
            CreatorSubscription.objects.filter(
                subscriber=self.user,
                creator=self.creator,
                status=CreatorSubscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists()
        )

    def test_non_subscriber_cannot_access_creator_content(self):
        """User not subscribed to creator should not access creator content."""
        self.assertFalse(
            CreatorSubscription.objects.filter(
                subscriber=self.user,
                creator=self.creator,
                status=CreatorSubscription.STATUS_ACTIVE,
                pending_approval=False,
            ).exists()
        )