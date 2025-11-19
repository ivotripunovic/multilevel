from django.conf import settings
from django.db import models
import uuid

def _generate_referral_code():
    # produce a 32-char hex string to fit the CharField(max_length=32)
    return uuid.uuid4().hex[:32]

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    # ensure stored default is a 32-char string (hex) not a UUID() object or 36-char string
    referral_code = models.CharField(max_length=32, unique=True, default=_generate_referral_code)
    referred_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile({self.user_id})"

class Commission(models.Model):
    """
    Record of a commission distributed to an upline user.
    """
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commissions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    source_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commission_sources")
    level = models.PositiveSmallIntegerField()  # 1 = direct referrer, 2 = referrer-of-referrer, etc.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Commission {self.amount} to {self.recipient} (lvl {self.level})"
