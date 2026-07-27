# Local patches

Changes we carry on top of upstream PyDDNS. They are kept as patch files
rather than merged into this fork's branches so the delta stays reviewable:
each file is one self-contained change with its reasoning in the diff itself.

Applied in filename order against upstream commit
`199ddc5b1833da489cee0dee3af53380a703abc4`:

| Patch | What it does |
|---|---|
| `0001-split-dns-resolver-host` | `DNS_RESOLVER_HOST` splits "where do I read the current record" from "where do I POST the update", which upstream conflates in `DNS_HOST`. Also makes the lookup ask for the RRtype it is about to write, and compare parsed addresses rather than strings — otherwise every IPv6 poll rewrites an unchanged record. |
| `0002-psycopg2-binary-cp314-wheels` | `psycopg2-binary` 2.9.10 → 2.9.12, the only pin without a cp314 wheel. Lets the image run on Python 3.14. |
| `0003-myip-auto-client-ip-fallback` | `myip=auto` and an omitted `myip` fall back to the client address. dyndns2 allows both, many routers rely on it, and the project's own dashboard hands out a `myip=auto` command — which stock upstream answers with `dnserr`. |
| `0004-dual-stack-myipv6` | Reads `myipv6` and updates it alongside `myip`, one call per address family. Upstream ignores the parameter, so a FritzBox-style `?myip=<ipaddr>&myipv6=<ip6addr>` answered `good` while never touching the AAAA. |
| `0005-delete-aaaa-when-cleared` | `myipv6` present but empty removes the AAAA — a host that permanently loses IPv6 would otherwise keep a stale record that clients prefer over the A and then time out on. Adds an explicit `delete` value for both families. |
| `0006-log-and-show-ipv6` | `Activity_log` gains an `ip6` column (with migration) and the dashboard shows it, so a dual-stack update is visible as such. |
| `0007-wider-shell-and-ip-wrap` | Dashboard layout: the data tables span the full width with the quickstart card below them, and a long IPv6 wraps instead of overlapping the neighbouring column. |

## Applying

```sh
git checkout --detach 199ddc5b1833da489cee0dee3af53380a703abc4
for p in patches/*.patch; do git apply --verbose "$p"; done
```

Deliberately plain `git apply`, **not** `--3way`. If upstream moves the code
out from under a patch, this has to fail loudly: a fuzzy merge that half
applies would produce a build that starts, serves, and then misbehaves in ways
that only show up in DNS — e.g. `DNS_RESOLVER_HOST` silently gone, leaving
every update to stall for the resolver's full 5s timeout before it writes.

Order matters: 0003 builds on 0001, and 0004/0005/0006 build on 0003.
