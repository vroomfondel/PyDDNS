import ipaddress


def get_client_ip(request):
    """Return the real client IP.
    """
    remote = request.META.get('REMOTE_ADDR', '')
    try:
        if ipaddress.ip_address(remote).is_private:
            forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
            if forwarded:
                return forwarded.split(',')[0].strip()
    except ValueError:
        pass
    return remote


def getForwardedFor(request):
    """Legacy display helper retained for backwards compatibility with
    pre-existing Activity_log rows. New code should use get_client_ip()."""
    FORWARDED_FOR_FIELDS = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_HOST',
        'HTTP_X_FORWARDED_SERVER',
    ]
    res = request.META.get('REMOTE_ADDR', '')
    for field in FORWARDED_FOR_FIELDS:
        if field in request.META:
            res = res + ' ' + request.META[field]
    return res
