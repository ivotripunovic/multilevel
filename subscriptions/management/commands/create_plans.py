from django.core.management.base import BaseCommand
from decimal import Decimal
from subscriptions.models import Plan


class Command(BaseCommand):
    help = "Create default subscription plans (monthly and yearly)"

    def handle(self, *args, **options):
        plans_data = [
            {
                "key": "monthly_pro",
                "name": "Pro Plan - Monthly",
                "price": Decimal("9.99"),
                "billing_period": "monthly",
                "active": True,
            },
            {
                "key": "yearly_pro",
                "name": "Pro Plan - Yearly",
                "price": Decimal("99.99"),
                "billing_period": "yearly",
                "active": True,
            },
            {
                "key": "monthly_basic",
                "name": "Basic Plan - Monthly",
                "price": Decimal("4.99"),
                "billing_period": "monthly",
                "active": True,
            },
            {
                "key": "yearly_basic",
                "name": "Basic Plan - Yearly",
                "price": Decimal("49.99"),
                "billing_period": "yearly",
                "active": True,
            },
        ]

        for plan_data in plans_data:
            plan, created = Plan.objects.get_or_create(
                key=plan_data["key"],
                defaults={
                    "name": plan_data["name"],
                    "price": plan_data["price"],
                    "billing_period": plan_data.get("billing_period", "monthly"),
                    "active": plan_data["active"],
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created plan: {plan.name} (${plan.price})")
                )
            else:
                self.stdout.write(self.style.WARNING(f"Plan already exists: {plan.name}"))