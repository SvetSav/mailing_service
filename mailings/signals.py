from django.core.cache import cache
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Attempt


@receiver(post_save, sender=Attempt)
def clear_stats_cache(sender, instance, **kwargs):
    owner_id = instance.mailing.owner_id
    cache.delete(f"stats_user_{owner_id}")
    cache.delete(f"home_stats_user_{owner_id}")
