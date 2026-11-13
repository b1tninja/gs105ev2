# Reporting a vulnerability

If you believe you have found a security issue in a device or protocol
discussed in this repository, please report it privately first, via the
contact in the repository's commit history or profile.

What to expect:

- An acknowledgment within a week.
- Findings coordinated privately while a vendor fix or mitigation is
  available; typical window is up to 90 days, shorter for issues reachable
  over the network with no authentication.
- Credit on request if you would like it after publication.

Please do not open public issues for unpatched vulnerabilities — use the
contact above; ordinary bugs in the scripts here are fine as issues.

## Scope of tooling in this repository

Everything under `tools/` is written to be **read-only** against the
switch unless its own docstring says otherwise: it sends an NSDP discovery
broadcast and reports replies, or reads the web UI, without changing
configuration. Nothing here is intended to write configuration, flash
firmware, or exploit the known authentication-bypass/overflow advisories
cited in [`docs/research.md`](docs/research.md) — those would be a separate,
explicitly scoped and authorized step against hardware the author owns.
