from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    # Ignore raw fixture loading
    if kwargs.get('raw', False):
        return

    if created:
        # Brand-new account — drop in a fresh profile row
        Profile.objects.create(user=instance)
    else:
        # Existing account — recover a missing profile if needed
        profile, _ = Profile.objects.get_or_create(user=instance)
        profile.save()