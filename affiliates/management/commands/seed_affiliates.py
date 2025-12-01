"""
Seed affiliate users and profiles for demo/testing.
Creates a root demo user and a tree of referred users up to depth 3.

Usage:
    python manage.py seed_affiliates --count 100 --demo-username demo_user --password password  
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import random

from affiliates.models import Profile

User = get_user_model()


def depth_from_user_to_root(user, root_user):
    """
    Return number of steps from `user` up to `root_user`.
    - If user == root_user -> 0
    - If root_user not in ancestry -> None
    """
    if user == root_user:
        return 0
    cur = user
    depth = 0
    # climb until we either reach root_user or the chain ends
    while True:
        prof = getattr(cur, "profile", None)
        if not prof or not prof.referred_by:
            return None
        depth += 1
        cur = prof.referred_by
        if cur == root_user:
            return depth


class Command(BaseCommand):
    help = "Seed 100 users and profiles for affiliate demo (creates demo_user as root)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", "-n", type=int, default=100, help="Number of users to create (including demo_user)"
        )
        parser.add_argument(
            "--demo-username", type=str, default="demo_user", help="Username for the root demo user"
        )
        parser.add_argument(
            "--password", type=str, default="password", help="Password for seeded users"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        count = options["count"]
        demo_username = options["demo_username"]
        pw = options["password"]

        # Create or get demo root user
        demo_user, created = User.objects.get_or_create(
            username=demo_username,
            defaults={"email": f"{demo_username}@example.com"}
        )
        if created:
            demo_user.set_password(pw)
            demo_user.save()
            self.stdout.write(self.style.SUCCESS(f"Created demo root user: {demo_user.username}"))
        else:
            self.stdout.write(f"Using existing demo user: {demo_user.username}")

        # Ensure demo profile exists and has referral code
        demo_profile, _ = Profile.objects.get_or_create(user=demo_user)
        demo_profile.refresh_from_db()

        existing_profiles = [demo_profile]

        next_idx = 1
        # create until we have `count` users total (including demo)
        while len(existing_profiles) < count:
            username = f"user_{next_idx:03d}"
            next_idx += 1
            if User.objects.filter(username=username).exists():
                continue

            email = f"{username}@example.com"
            user = User.objects.create_user(username=username, email=email, password=pw)
            prof, _ = Profile.objects.get_or_create(user=user)
            prof.refresh_from_db()

            # choose a referrer among existing profiles whose depth to demo_user is < 3
            candidates = []
            for p in existing_profiles:
                d = depth_from_user_to_root(p.user, demo_user)
                # p.user can be used as a referrer if they are in the demo tree and their depth < 3
                # demo_user has depth 0 -> allowed; others allowed while depth < 3 so new user stays <=3
                if d is not None and d < 3:
                    candidates.append(p)

            # fallback: if no candidates (shouldn't happen), use demo_profile
            if not candidates:
                candidates = [demo_profile]

            chosen = random.choice(candidates)
            prof.referred_by = chosen.user
            prof.save()

            existing_profiles.append(prof)

            self.stdout.write(f"Created {user.username} referred_by={chosen.user.username}")

        self.stdout.write(self.style.SUCCESS(f"Seeding complete: {len(existing_profiles)} profiles created."))
        self.stdout.write("Demo root user referral link:")
        self.stdout.write(f"/accounts/register/?ref={demo_profile.referral_code}")