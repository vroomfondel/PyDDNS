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
| `0008-show-live-aaaa-in-domain-table` | The domain table shows the AAAA that is live in DNS. Resolved rather than read from `Activity_log`: its newest good row has an empty `ip6` both when a v4-only update did not mention v6 (AAAA still valid) and when one explicitly cleared it (AAAA gone) — two opposite states, one representation. |
| `0009-resolve-v4-from-dns-too` | The v4 column resolves from DNS as well. `last_ip` returned what the client last *reported*, which drifts from what is published as soon as a record changes by any other route. Renamed to `current_ip` rather than quietly redefined. |

## DNS backend

Several of these patches assume the DNS write path is
[**pyddns-nsupdate**](https://github.com/vroomfondel/pyddns-nsupdate) rather
than `davd/docker-ddns`, which upstream pairs with and which has been
amd64-only and unpublished since 2020. It speaks the same
`/update?secret=&domain=&addr=` contract and turns each call into a
TSIG-signed RFC 2136 update against a nameserver you already run.

**`0005` requires it.** That patch calls a `/delete` endpoint, which is the one
place the contract goes beyond davd's API. Against the original backend the
call returns 404 and surfaces to the client as `dnserr`, so the AAAA is never
removed — the exact failure the patch exists to prevent. If you apply `0005`,
use that backend.

`0001` also assumes it, though less strictly: stock PyDDNS derives both the
update API address and the nameserver it queries from `DNS_HOST`, expecting
one host to answer both. pyddns-nsupdate only writes; `0001` splits the two
settings so reads go straight to the authoritative server.

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
