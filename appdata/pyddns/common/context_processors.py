"""Template context processors that expose selected settings to all templates."""
from django.conf import settings


def site_context(request):
    """Expose DNS-related settings (and other safe values) to every template."""
    return {
        'DNS_DOMAIN': getattr(settings, 'DNS_DOMAIN', None) or '',
        'OWN_ADMIN': getattr(settings, 'OWN_ADMIN', '0') == '1',
        'LANGUAGE_LOCKED': getattr(settings, 'LANGUAGE_LOCKED', False),
    }
