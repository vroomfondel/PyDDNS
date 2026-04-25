def getForwardedFor(request):
    FORWARDED_FOR_FIELDS = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_FORWARDED_HOST',
        'HTTP_X_FORWARDED_SERVER',
    ]
    res = request.META['REMOTE_ADDR']
    for field in FORWARDED_FOR_FIELDS:
        if field in request.META:
            res = res + ' ' + request.META[field]
    return res
