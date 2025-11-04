from django.conf import settings
from decimal import Decimal
from .models import Commission, Profile

# Example level rates; tune per business rules or store in DB/config
LEVEL_RATES = [Decimal('0.10'), Decimal('0.05'), Decimal('0.02')]  # 10%, 5%, 2% for levels 1..3

def get_upline_users(user, max_levels=None):
    """
    Walk up the referral tree and yield (user, level) pairs.
    """
    if max_levels is None:
        max_levels = len(LEVEL_RATES)
    upline = []
    current = getattr(user, "profile", None)
    level = 0
    while current and current.referred_by and level < max_levels:
        level += 1
        parent_user = current.referred_by
        upline.append((parent_user, level))
        current = getattr(parent_user, "profile", None)
    return upline

def distribute_commissions(source_user, amount):
    """
    Create commission records for upline according to LEVEL_RATES.
    amount: Decimal or numeric sale amount
    """
    from decimal import Decimal
    amt = Decimal(amount)
    upline = get_upline_users(source_user)
    for (recipient, level) in upline:
        try:
            rate = LEVEL_RATES[level - 1]
        except IndexError:
            break
        commission_amount = (amt * rate).quantize(Decimal('0.01'))
        if commission_amount > 0:
            Commission.objects.create(
                recipient=recipient,
                amount=commission_amount,
                source_user=source_user,
                level=level
            )