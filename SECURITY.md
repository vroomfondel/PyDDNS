# Security Policy

## Reporting a Vulnerability

If you have discovered a security vulnerability in PyDDNS, please report it
**privately** so we can address it before public disclosure.

- **Preferred channel:** open a [GitHub Security Advisory](https://github.com/olimpo88/PyDDNS/security/advisories/new) (private to maintainers).
- **Alternative:** contact the maintainer through [LinkedIn](https://www.linkedin.com/in/peraltaleandro/).

Please **do not** open a public GitHub issue for security vulnerabilities.

When reporting, include:

- A clear description of the vulnerability and its impact.
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected version(s) or commit hash.
- Any suggested mitigation, if you have one.

## Response Expectations

- **Acknowledgment:** within 7 days of receiving the report.
- **Fix timeline:** depends on severity, typically 7–30 days for confirmed
  high-severity issues.
- **Disclosure:** we coordinate public disclosure with the reporter once a
  fix is available, and credit the reporter in the release notes unless they
  prefer to remain anonymous.

## Supported Versions

Only the latest minor version is actively patched. If you are running an
older release, plan to upgrade before reporting unless the issue is
demonstrably present in the latest version as well.

| Version | Supported |
|---------|-----------|
| 3.x     | ✅ |
| 2.x     | ❌ (end-of-life — see [migration guide](README.md#-migrating-from-postgres-96)) |
| 1.x     | ❌ |

## Scope

In scope:

- The Django application (`appdata/pyddns/`)
- The Docker Compose deployment
- Authentication and authorization flows
- The dyndns2 update endpoint (`/nic/update`)

Out of scope:

- Third-party images (`davd/docker-ddns`, `postgres:15`, `nginx:1.27`) —
  please report upstream.
- Issues that require already-compromised admin credentials (privilege
  escalation by an authenticated administrator is expected — admins control
  user accounts and DNS records by design).
- Self-signed certificates in test environments.
- Social engineering of project maintainers.

## Disclosure Hall of Fame

Credited reporters will be listed here as advisories are published.
