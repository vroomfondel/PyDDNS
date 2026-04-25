<div align="center">

<img src="https://i.imgur.com/kOrgTBW.png" alt="PyDDNS" width="320" />

# PyDDNS — Self-Hosted Dynamic DNS Server

**Run your own `dyndns2`-compatible DNS service. No vendor lock-in, no monthly fees, no rate limits.**

[![Tests](https://github.com/olimpo88/PyDDNS/actions/workflows/test.yml/badge.svg)](https://github.com/olimpo88/PyDDNS/actions/workflows/test.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/python-3.11-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)
[![Django](https://img.shields.io/badge/Django-5.2%20LTS-092E20.svg?logo=django&logoColor=white)](https://www.djangoproject.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com)

[Quick Start](#-quick-start) · [Features](#-features) · [Use Cases](#-use-cases) · [Roadmap](#-roadmap) · [Contributing](#-contributing)

</div>

---

## 🌟 Why PyDDNS?

Public Dynamic DNS providers come with caveats: rate limits, paid tiers, branded subdomains, and data you don't own. **PyDDNS** is the self-hosted, production-ready alternative — a complete DDNS solution wrapped in a clean web UI and one-command Docker deployment.

Point a delegated subdomain at your server, create user accounts, and let users update their public IP from any standard `dyndns2` client — router firmware, `ddclient`, `inadyn`, mobile apps. DNS lives in your own BIND zone, activity is fully logged, and access is gated per-user.

> 📺 **See it in action:** [demo video](https://www.youtube.com/watch?v=ALN9901EoyA)

![PyDDNS web interface](https://i.imgur.com/6HTwrfn.png)

---

## ✨ Features

- 🔌 **`dyndns2` protocol compatible** — drop-in replacement for No-IP, DynDNS, Duck DNS, with any existing client
- 👥 **Multi-user, multi-domain** — admin panel, per-user subdomains, role-based permissions
- 🔐 **Production-grade security** — Gunicorn behind nginx, HTTPS, secure cookies, hardened headers, env-driven secrets
- 📊 **Full audit trail** — every IP update, login attempt, and admin action persisted to Postgres
- 🌍 **i18n out of the box** — English, Spanish, German, Japanese, Simplified Chinese
- 🧰 **One-command deployment** — `docker compose up -d` and you're live
- 🩺 **Healthchecks everywhere** — Postgres, Gunicorn, and TCP probes baked into Compose
- 🧪 **Tested in CI** — pytest suite + GitHub Actions on every push
- 🔄 **Smooth upgrades** — scripted Postgres 9.6 → 15 migration for v1/v2 deployments

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | [Django 5.2 LTS](https://www.djangoproject.com) on [Python 3.11](https://www.python.org) |
| WSGI | [Gunicorn 23](https://gunicorn.org) — 3 workers in production, `--reload` in development |
| DNS | [BIND](https://www.isc.org/bind/) via [`davd/docker-ddns`](https://hub.docker.com/r/davd/docker-ddns) |
| Database | [PostgreSQL 15](https://www.postgresql.org) |
| Reverse Proxy | [nginx 1.27](https://nginx.org) — HTTPS termination, static files |
| Orchestration | [Docker Compose v2](https://docs.docker.com/compose/) — multi-stage build, non-root container |
| Testing | [pytest](https://pytest.org), [pytest-django](https://pytest-django.readthedocs.io), [ruff](https://docs.astral.sh/ruff/) |
| CI | [GitHub Actions](https://github.com/features/actions) — tests + lint on every push |

---

## 🚀 Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/install/) and [Docker Compose v2](https://docs.docker.com/compose/install/)
- A delegated subdomain (e.g. `ddns.example.com`) pointing to your server's public IP
- Ports 53 (TCP/UDP), 80, and 443 reachable from the internet

> **Ubuntu 18+ users:** see [troubleshooting](#-troubleshooting) about freeing port 53 from `systemd-resolved`.

### Installation

```bash
git clone https://github.com/olimpo88/PyDDNS.git
cd PyDDNS

# 1. Configure environment
cp .env-demo .env

# 2. Generate a Django secret key and paste it into DJANGO_SECRET_KEY in .env
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(50))"

# 3. Build and start the stack
docker compose build
docker compose up -d

# 4. Watch services become healthy
docker compose ps
```

All four services — `python`, `postgres`, `nginx`, `ddns` — should reach `(healthy)` within ~30 seconds. The web UI is on `HTTP_PORT` (80 by default); log in with `DJANGO_SU_NAME` / `DJANGO_SU_PASSWORD` defined in `.env`.

---

## 🔧 Configuration

Environment variables live in `.env` (template: [`.env-demo`](.env-demo)).

| Variable | Purpose | Required |
|----------|---------|:-:|
| `DOMAIN` | Delegated subdomain (e.g. `ddns.example.com`) | ✅ |
| `SHARED_SECRET` | Internal API token between Django and BIND | ✅ |
| `DJANGO_SECRET_KEY` | Cryptographic signing key | ✅ |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated valid `Host` headers | ✅ |
| `DJANGO_SETTINGS_MODULE` | `pyddns.settings.production` or `.development` | ✅ |
| `DJANGO_LANGUAGE_CODE` | UI language (`en`, `es`, `de`, `ja`, `zh-hans`) | ➖ |
| `DJANGO_TIME_ZONE` | TZ database name (default `UTC`) | ➖ |
| `DATABASE_NAME` / `_USER` / `_PASS` | PostgreSQL connection | ✅ |
| `DJANGO_SU_NAME` / `_EMAIL` / `_PASSWORD` | Bootstrap admin user | ✅ |
| `DJANGO_ADMIN_URL` | Path of `/admin` (rename for security through obscurity) | ➖ |
| `DNS_ALLOW_AGENT` | Comma-separated User-Agent allowlist | ➖ |
| `COMPOSE_PROFILES` | Set to `migration` to run Postgres 9.6 → 15 upgrade | ➖ |

### Development mode

```ini
DJANGO_DEBUG=1
DJANGO_SETTINGS_MODULE=pyddns.settings.development
```

Then `docker compose restart python` — Gunicorn picks up code changes automatically via `--reload`.

<details>
<summary><strong>DNS zone setup (NS delegation, glue records)</strong></summary>

You need a delegated subdomain. Create an **NS record** in your parent zone:

```
ddns.example.com IN NS X.X.X.X
```

Example BIND zone for delegation:

```
ddns.example.com.   IN  A   X.X.X.X
$ORIGIN ddns.example.com.
@                   IN  NS  ddns.example.com.
```

To edit the zone file directly (e.g. for static records):

```bash
docker compose exec ddns bash
rndc freeze ddns.example.com
# edit data/bind-data/ddns.example.com.zone
rndc thaw ddns.example.com
```
</details>

<details>
<summary><strong>SSL / HTTPS configuration</strong></summary>

The default nginx config exposes both HTTP (`HTTP_PORT`) and HTTPS (`HTTPS_PORT`).

For testing, generate a self-signed certificate:

```bash
mkdir -p data/certs/
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout data/certs/https.key -out data/certs/https.crt
```

For production, drop your CA-issued `https.crt` and `https.key` into `data/certs/` (Let's Encrypt, Cloudflare Origin, your own CA, etc.).

To remove HTTPS entirely, delete the `listen 8443 ssl;` server block from `config/nginx/mydjango.conf`.
</details>

---

## 🖥 DDNS Clients

Any `dyndns2`-compatible client works.

### Linux / macOS — `ddclient`

```ini
protocol=dyndns2
use=web, web=checkip.dyndns.com, web-skip='IP Address'
server=ddns.example.com
ssl=yes
login=youruser
password='yourpassword'
yourdomain.ddns.example.com
```

### Windows

[DynDNS Simply Client](https://sourceforge.net/projects/dyndnssimplycl/) — free and lightweight.

### Routers

ASUS, MikroTik, OpenWrt, OPNsense, pfSense, and most consumer routers ship with `dyndns2` support. Use the *Custom DNS* option and point it at your PyDDNS instance.

---

## 💡 Use Cases

- 🏠 **Home server access** — expose your NAS, IP cameras, or self-hosted services without paying for a static IP
- 🧪 **Lab and staging environments** — give every developer a stable subdomain that follows their dev VPN
- 🏢 **SMB infrastructure** — internal DDNS for branch offices, ISP-rotated IPs, or remote-worker VPN endpoints
- 🌍 **Sovereign deployments** — sidestep public DDNS providers that block your country, ISP, or charge premium tiers
- 🔒 **Privacy-first setups** — keep IP rotation patterns out of third-party logs

---

## 🌐 Internationalization

Languages shipped: 🇺🇸 English · 🇪🇸 Spanish · 🇩🇪 German · 🇯🇵 Japanese · 🇨🇳 Simplified Chinese.

Browser auto-detection via `Accept-Language` is on by default. Override per-deployment with `DJANGO_LANGUAGE_CODE`.

To add or update a translation:

```bash
docker compose exec python python manage.py makemessages --locale <code>
# Edit appdata/pyddns/locale/<code>/LC_MESSAGES/django.po
docker compose exec python python manage.py compilemessages
```

---

## 🧪 Testing

51 tests cover models, views, the dyndns2 protocol, settings hardening, and DNS update flows.

```bash
docker compose exec python pip install pytest==7.4.4 pytest-django==4.8.0
docker compose exec python python -m pytest -v
```

Pushes and pull requests automatically run the full suite against PostgreSQL 15 via [GitHub Actions](.github/workflows/test.yml).

---

## 🔄 Migrating from Postgres 9.6

PyDDNS v3+ runs on PostgreSQL 15. If you're upgrading from a 9.6-based release, the included script handles a side-by-side `pg_dump` → `psql` migration with both versions running in parallel under a Compose profile:

```bash
./scripts/migrate-postgres.sh
```

The script preserves your old data directory in `data/dbdata-old/` until you confirm the new cluster works. Full details in the [`scripts/migrate-postgres.sh`](scripts/migrate-postgres.sh) header.

---

## 🗺 Roadmap

- [ ] **API tokens** — issue revocable per-user tokens, replacing HTTP Basic in dyndns2 update
- [ ] **IPv6 (AAAA records)** — first-class support for IPv6-only and dual-stack updates
- [ ] **Webhook notifications** — POST to a user-configured URL on every update or anomaly
- [ ] **Prometheus metrics** — scraping endpoint for sync rates, login failures, zone health
- [ ] **OAuth / OIDC login** — optional SSO via Authentik, Keycloak, GitHub
- [ ] **Per-user rate limits** — configurable abuse protection beyond the global threshold
- [ ] **Two-factor authentication** — TOTP for admin and end-user accounts
- [ ] **REST API** — full CRUD for users and subdomains, OpenAPI spec
- [ ] **UI refresh** — modernized templates, dark mode, mobile-first layout

Have an idea? [Open an issue](https://github.com/olimpo88/PyDDNS/issues/new).

---

## 🤝 Contributing

Contributions are welcome — bug reports, translation updates, documentation polish, and pull requests alike.

1. **Fork** the repository and clone your fork.
2. **Create a branch**: `git checkout -b feat/your-feature`.
3. **Run tests locally** before pushing:
   ```bash
   docker compose exec python python -m pytest -v
   ```
4. **Open a pull request** against `master`, describing the change and linking any related issues.

Please follow the existing code style: Django conventions for Python, `ruff` for linting, conventional commit messages where practical.

---

## 📜 License

PyDDNS is licensed under the **GNU Affero General Public License v3.0 (AGPLv3)**. See [`LICENSE`](LICENSE) for the full text and the additional Section 7 attribution clause.

What this means in plain English:

- ✅ You can use, modify, and run PyDDNS commercially
- ✅ You can host it as a paid service for others
- ⚠️ If you modify it, including operating a modified version as a network service (SaaS), you must publish your modifications under the same license
- ⚠️ The in-app attribution footer linking to the original repository must remain visible in any derivative

---

## 🙏 Acknowledgments

PyDDNS builds on the excellent [`docker-ddns`](https://github.com/dprandzioch/docker-ddns) image by **dprandzioch**. PyDDNS adds the multi-tenant Django front-end, audit logging, web management UI, and an opinionated production deployment.

---

## 🛟 Troubleshooting

<details>
<summary><strong>Port 53 already in use (Ubuntu 18+, systemd-resolved)</strong></summary>

```bash
sudo lsof -i :53
```

If `systemd-resolve` is bound, edit `/etc/systemd/resolved.conf`:

```ini
[Resolve]
DNS=1.1.1.1
DNSStubListener=no
```

Then symlink the resolver and reboot:

```bash
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
sudo reboot
```
</details>

<details>
<summary><strong>Postgres 15 fails to start with "incompatible data directory"</strong></summary>

You're upgrading from Postgres 9.6 and haven't migrated yet. Run [`./scripts/migrate-postgres.sh`](#-migrating-from-postgres-96) before `docker compose up`.
</details>

<details>
<summary><strong>"DJANGO_SECRET_KEY environment variable is required"</strong></summary>

The app refuses to start without a secret key. Generate one and add it to `.env`:

```bash
docker run --rm python:3.11-slim python -c "import secrets; print(secrets.token_urlsafe(50))"
```
</details>

---

## 📬 Contact

**Leandro Peralta** — [LinkedIn](https://www.linkedin.com/in/peraltaleandro/) · [GitHub](https://github.com/olimpo88)

If PyDDNS is useful to you, ⭐ the repo — it's the cheapest way to support an open-source author.

---

<div align="center">
<sub>Keywords: dynamic DNS, self-hosted DDNS, dyndns2 server, ddclient server, BIND web UI, Django DDNS, Docker DDNS, no-ip alternative, duckdns alternative, AGPL DNS</sub>
</div>
