import uuid
from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


def _generate_referral_code():
    # produce a 32-char hex string to fit the CharField(max_length=32)
    return uuid.uuid4().hex[:32]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    # ensure stored default is a 32-char string (hex) not a UUID() object or 36-char string
    referral_code = models.CharField(max_length=32, unique=True, default=_generate_referral_code)
    # store who referred this user (upline)
    referred_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile(user_id={self.user_id}, referral_code={self.referral_code})"


class Commission(models.Model):
    """
    Commission record created when distribute_commissions runs.
    Fields match how affiliates.utils.create() expects them: recipient, source_user, level, amount.
    """
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="commissions")
    source_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="generated_commissions")
    level = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Commission(recipient={getattr(self.recipient, 'username', self.recipient)}, amount={self.amount}, level={self.level})"
