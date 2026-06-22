from django.core.cache import cache
from .models import SiteSettings

_CACHE_KEY = "site_settings_singleton"
_CACHE_TTL = 3600  # 1 hour


def site_settings(request):
    site = cache.get(_CACHE_KEY)
    if site is None:
        site = SiteSettings.get()
        cache.set(_CACHE_KEY, site, _CACHE_TTL)
    return {"site": site}
