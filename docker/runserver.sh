#!/bin/bash
set -e

cd /usr/src/app
if [ ! -f manage.py ]; then
    django-admin startproject app .
fi

python manage.py makemigrations
python manage.py migrate --noinput

if [[ ! -z "${DJANGO_SU_NAME}" ]]; then
    echo "from django.contrib.auth.models import User; User.objects.filter(username='$DJANGO_SU_NAME').exists() or  User.objects.create_superuser('$DJANGO_SU_NAME', '$DJANGO_SU_EMAIL', '$DJANGO_SU_PASSWORD')" | python manage.py shell
fi

# Worker count is overridable via GUNICORN_WORKERS. Default 3 is fine for
# a few hundred clients; bump it for higher fanout (e.g. 1000+ devices).
# Each worker holds one persistent DB connection (see DB_CONN_MAX_AGE),
# so size workers and Postgres `max_connections` together.
case "${DJANGO_DEBUG:-0}" in
    1|true|True|TRUE|yes|Yes)
        GUNICORN_OPTS="--workers 1 --reload"
        ;;
    *)
        GUNICORN_OPTS="--workers ${GUNICORN_WORKERS:-3}"
        ;;
esac

# Daily Activity_log retention sweep. Runs once an hour after startup
# (idempotent — only deletes rows older than ACTIVITY_LOG_RETENTION_WEEKS).
# Skipped when retention is set to 0.
RETENTION="${ACTIVITY_LOG_RETENTION_WEEKS:-10}"
if [ "$RETENTION" -gt 0 ] 2>/dev/null; then
    (
        # Wait a minute on boot so migrations and the bootstrap superuser
        # creation above finish first; then sleep a day between sweeps.
        sleep 60
        while true; do
            python manage.py prune_activity_log >/dev/null 2>&1 || true
            sleep 86400
        done
    ) &
fi

exec gunicorn pyddns.wsgi:application \
    --bind 0.0.0.0:8000 \
    $GUNICORN_OPTS \
    --access-logfile - \
    --error-logfile -
