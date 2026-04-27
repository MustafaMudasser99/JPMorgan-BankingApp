from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Account, UserProfile
from decimal import Decimal

@receiver(post_save, sender=User)
def create_default_accounts(sender, instance, created, **kwargs):
    """
    Signal to create the mandatory Current account when a new user is created.
    Only runs when a new user is created (not on updates).
    """
    if created:
        # Ensure a profile exists for OOBE + preferences
        UserProfile.objects.get_or_create(user=instance)

        # Check if the user already has accounts (to prevent duplicates)
        existing_qs = Account.objects.filter(user=instance)

        if not existing_qs.exists():
            # Create Current Account
            Account.objects.create(
                name=f"{instance.first_name or instance.username}'s Current Account",
                starting_balance=Decimal('1000.00'),
                round_up_enabled=False,
                user=instance,
                account_type='current'
            )
    else:
        # Also ensure profile exists for legacy users created before this feature.
        UserProfile.objects.get_or_create(user=instance)