from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, **kwargs):
    profile, _ = Profile.objects.get_or_create(user=instance)
    if profile.referral_code != instance.username:
        profile.referral_code = instance.username
        profile.save(update_fields=["referral_code"])
