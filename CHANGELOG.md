# Changelog

All notable changes to PyDDNS are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.0] — 2026-04-25

Major modernization release. Stack upgraded end-to-end, security hardened,
test coverage added, deployment automated.

### Breaking changes

- **Postgres 9.6 → 15.** Existing v1/v2 deployments must run
  `./scripts/migrate-postgres.sh` before upgrading; the script preserves the
  9.6 cluster in `data/dbdata-old/` until you confirm the migration.
- **`DJANGO_SECRET_KEY` is now required.** The application refuses to start
  without it. Generate one with
  `docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(50))"`.
- **`DJANGO_ALLOWED_HOSTS` is required in production.** Empty value triggers
  a startup error.
- **WSGI server changed from Django dev server to Gunicorn.** Set
  `DJANGO_DEBUG=1` and `DJANGO_SETTINGS_MODULE=pyddns.settings.development`
  to keep auto-reload behavior in development.
- **Settings split.** `pyddns.settings` is now a package with
  `base / development / production` modules. `DJANGO_SETTINGS_MODULE` must
  point at one of the leaves.

### Added

- Argon2id password hashing (PBKDF2 fallback for transitioning legacy hashes)
- HSTS, `SECURE_SSL_REDIRECT`, `SECURE_REFERRER_POLICY`, hardened cookies in production
- nginx hardening: TLS 1.2/1.3 only, modern ciphers, `server_tokens off`, Permissions-Policy
- Per-user brute-force throttle on `/nic/update` (in addition to existing per-IP)
- Input validation on subdomain names (DNS-label regex) and IP addresses
- Container hardening: `cap_drop: ALL`, `no-new-privileges`, `read_only` filesystem
- One-command Postgres 9.6 → 15 migration via Compose profile + `scripts/migrate-postgres.sh`
- `pyddns.settings.development` and `pyddns.settings.production` split
- pytest suite (75+ tests) covering models, views, dyndns2 protocol, settings
- GitHub Actions CI running tests + ruff against Postgres 15
- Healthchecks for `postgres`, `python`, plus `service_healthy` `depends_on` gates
- `requirements-dev.txt` with pytest, pytest-django, ruff
- `SECURITY.md`, `CHANGELOG.md`, redesigned `README.md`

### Changed

- Python 3.7 → 3.11 (multi-stage Dockerfile, non-root `app` user)
- Django 3.x → 5.2 LTS (supported through April 2028)
- nginx pinned to `1.27` (no more floating `latest`)
- All `url(r'...')` migrated to `re_path(r'...')`
- `ugettext_lazy` migrated to `gettext_lazy`
- `LANGUAGES` now matches the locale directories (`es`, `en`, `ja`, `de`, `zh-hans`)
- `LANGUAGE_CODE` and `TIME_ZONE` configurable via `DJANGO_LANGUAGE_CODE` / `DJANGO_TIME_ZONE`
- `dnspython` 1.16 → 2.6 (`resolver.query()` → `resolver.resolve()`)
- BIND HTTP call uses `requests` `params={}` dict (closes parameter pollution risk)
- `Activity_log` now uses timezone-aware `timezone.now()` (was naive `datetime.now()`)
- Real client IP now resolved via private-network proxy trust (closes spoofed-XFF brute-force bypass)

### Removed

- `django-datatables-view` dependency (was unused)
- ~540 lines of dead ExtJS/legacy code from `common/utils.py`
- Hardcoded `SECRET_KEY` in source
- Hardcoded `DEBUG = True` and `ALLOWED_HOSTS = ['*']`
- `wait-for-it.sh` (replaced by Compose healthcheck-gated `depends_on`)
- Forced HTTPS redirect block in nginx (replaced with proper `SECURE_SSL_REDIRECT` via Django)

### Fixed

- `add_user` view caught a non-existent `OstUserEmail.DoesNotExist` exception
  (would `NameError` on invalid `id_user`); now catches `User.DoesNotExist`
- Duplicate `name="login"` in `common/urls.py` made `reverse('common:login')`
  return the wrong URL
- Anonymous users could hit `add_subdomain` and `set_ip_web`, triggering 500s
  on missing IDs (information disclosure / enumeration); now `@login_required`
- Basic Auth credentials were logged in plain text on every `/nic/update`
  request; now redacted (only username, gated by `DEBUG`)
- `SecurityMiddleware` was missing from `MIDDLEWARE`, silently disabling all
  `SECURE_*` settings

### Security

See `SECURITY.md` for the disclosure policy. This release closes 2 critical,
7 high and 8 medium severity findings from an internal audit.

---

[Unreleased]: https://github.com/olimpo88/PyDDNS/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/olimpo88/PyDDNS/releases/tag/v3.0.0
