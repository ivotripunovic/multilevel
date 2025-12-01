import uuid

from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


def _generate_referral_code():
    # Legacy helper kept for historical migrations.
    return uuid.uuid4().hex[:32]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    # referral code now mirrors the username so links are human-readable
    referral_code = models.CharField(max_length=150, unique=True, editable=False)
    # store who referred this user (upline)
    referred_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.user_id and self.user and self.referral_code != self.user.username:
            self.referral_code = self.user.username
        super().save(*args, **kwargs)

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
