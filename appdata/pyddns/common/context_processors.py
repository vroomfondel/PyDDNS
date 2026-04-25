"""Template context processors that expose selected settings to all templates."""
from django.conf import settings


def site_context(request):
    """Expose DNS-related settings (and other safe values) to every template."""
    impersonator = None
    impersonator_id = None
    if hasattr(request, 'session'):
        impersonator_id = request.session.get('_impersonator_id')
    if impersonator_id:
        from django.contrib.auth import get_user_model
        try:
            impersonator = get_user_model().objects.get(id=impersonator_id)
        except get_user_model().DoesNotExist:
            impersonator = None

    return {
        'DNS_DOMAIN': getattr(settings, 'DNS_DOMAIN', None) or '',
        'OWN_ADMIN': getattr(settings, 'OWN_ADMIN', '0') == '1',
        'LANGUAGE_LOCKED': getattr(settings, 'LANGUAGE_LOCKED', False),
        'IS_IMPERSONATING': bool(impersonator),
        'IMPERSONATOR': impersonator,
    }
