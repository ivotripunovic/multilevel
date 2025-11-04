from django.conf import settings
from django.db import models
import uuid

User = settings.AUTH_USER_MODEL

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    referral_code = models.CharField(max_length=32, unique=True, default=uuid.uuid4)
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
