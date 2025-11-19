from django.conf import settings
from decimal import ROUND_HALF_UP, Decimal
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
        commission_amount = (amt * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        if commission_amount > 0:
            Commission.objects.create(
                recipient=recipient,
                amount=commission_amount,
                source_user=source_user,
                level=level
            )

def get_downline_users(user, max_levels=None):
    """
    Return a list of (user, level) for all users referred (directly or indirectly)
    by `user`. Level 1 = direct referrals, 2 = referrals of referrals, etc.
    Breadth-first traversal is used so nearer referrals come first.
    """
    from collections import deque
    from .models import Profile

    if max_levels is None:
        max_levels = len(LEVEL_RATES) if 'LEVEL_RATES' in globals() else None

    results = []
    q = deque()
    # start from the root user at level 0
    q.append((user, 0))

    while q:
        parent, lvl = q.popleft()
        next_level = lvl + 1
        if max_levels is not None and next_level > max_levels:
            continue
        # find direct referrals of `parent`
        for prof in Profile.objects.filter(referred_by=parent).select_related("user"):
            u = prof.user
            results.append((u, next_level))
            q.append((u, next_level))
    return results