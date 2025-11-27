from collections import deque
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple
import logging

from .models import Commission, Profile

logger = logging.getLogger(__name__)

# Example level rates; tune per business rules or store in DB/config
LEVEL_RATES = [Decimal('0.10'), Decimal('0.05'), Decimal('0.02')]  # 10%, 5%, 2% for levels 1..3


def get_upline_users(user, max_levels=None) -> List[Tuple[object, int]]:
    """
    Return list of (user, level) for the given user's upline.
    Level 1 is the direct referrer, level 2 is referrer's referrer, etc.
    Stops at max_levels if provided.
    """
    upline = []
    try:
        # Fetch profile directly from DB to ensure fresh data
        prof = Profile.objects.select_related("referred_by").get(user=user)
    except Profile.DoesNotExist:
        logger.debug("No Profile found for user=%r", user)
        return upline

    level = 0
    cur_user = user
    while True:
        try:
            prof = Profile.objects.select_related("referred_by").get(user=cur_user)
        except Profile.DoesNotExist:
            logger.debug("Profile not found for cur_user=%r", cur_user)
            break
        
        if not prof.referred_by:
            logger.debug("No referred_by for user=%r", cur_user)
            break
        
        level += 1
        parent = prof.referred_by
        upline.append((parent, level))
        logger.debug("Added to upline: %r at level %d", getattr(parent, "username", parent), level)
        
        if max_levels is not None and level >= max_levels:
            break
        cur_user = parent

    return upline


def distribute_commissions(source_user, amount):
    """
    Distribute commissions for a given amount paid/recorded by source_user.
    Creates Commission records for each applicable upline level based on LEVEL_RATES.
    Returns number of created Commission objects (useful for tests / debugging).
    """
    if not isinstance(amount, Decimal):
        try:
            amt = Decimal(str(amount))
        except Exception:
            amt = Decimal("0.00")
    else:
        amt = amount

    logger.debug("distribute_commissions called: source_user=%r amount=%r", source_user, amt)

    if amt <= Decimal("0"):
        logger.debug("Amount <= 0, nothing to distribute")
        return 0

    max_levels = len(LEVEL_RATES)
    upline = get_upline_users(source_user, max_levels=max_levels)
    logger.debug("Computed upline for %r: %s", source_user, [(getattr(u, "username", str(u)), lvl) for (u, lvl) in upline])

    created = 0
    for (recipient, level) in upline:
        try:
            rate = LEVEL_RATES[level - 1]
        except IndexError:
            logger.debug("No rate for level %d, stopping", level)
            break
        commission_amount = (amt * rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        try:
            # create Commission using the expected model field names
            Commission.objects.create(
                recipient=recipient,
                amount=commission_amount,
                source_user=source_user,
                level=level,
            )
            created += 1
            logger.debug(
                "Created commission: recipient=%r level=%d amount=%s",
                getattr(recipient, "username", recipient),
                level,
                commission_amount,
            )
        except Exception as exc:
            logger.exception(
                "Failed to create Commission for recipient=%r level=%d: %s",
                getattr(recipient, "username", recipient),
                level,
                exc,
            )

    logger.debug("distribute_commissions created %d commissions", created)
    return created


def get_downline_users(user, max_levels=None) -> List[Tuple[object, int]]:
    """
    Return list of (user, level) for the downline (all referred users) up to max_levels.
    Level 1 are direct referrals, level 2 are referrals-of-referrals, etc.
    BFS traversal to ensure level ordering.
    """
    results = []
    q = deque()
    # start from level 1 (direct referrals)
    q.append((user, 0))

    while q:
        cur_user, cur_level = q.popleft()
        next_level = cur_level + 1
        if max_levels is not None and next_level > max_levels:
            continue
        # find direct referrals
        referrals = Profile.objects.filter(referred_by=cur_user).select_related("user")
        for prof in referrals:
            referred_user = prof.user
            results.append((referred_user, next_level))
            q.append((referred_user, next_level))

    return results