# GS105Ev2 firmware

Official firmware images fetched 2026-11-13 from NETGEAR's download CDN.
Device: [`docs/GS105Ev2.md`](../../docs/GS105Ev2.md).

> **Do not commit these `.bin`/`.zip` files** to a public repository. They
> are NETGEAR firmware, redistributed only for local research / backup on
> owned hardware. See `../../.gitignore` and `../../LEGAL.md`.

## Available packages

| Version | File | Source URL | Release notes |
| --- | --- | --- | --- |
| 1.6.0.25 (current, 2026-07-02) | `GS105Ev2_V1.6.0.25.zip` | https://www.downloads.netgear.com/files/GDC/GS105EV2/GS105Ev2_V1.6.0.25.zip | Fixes management VLAN ID corruption on config restore. No other changes. |
| 1.6.0.4 (2019, prior, kept for comparison) | `GS105Ev2_V1.6.0.4.zip` | https://www.downloads.netgear.com/files/GDC/GS105EV2/GS105Ev2_V1.6.0.4.zip | Web GUI title fix; security fixes for PSV-2018-0538, PSV-2018-0542, PSV-2018-0612; ACL invalid IP/mask bugfix. |

Each zip contains one `.bin` image and one `*_Release_Notes.html`.

## Hashes

See [`HASHES.md`](HASHES.md) (zip-level and inner `.bin`-level SHA-256).

## Why two versions

1.6.0.4 is the last version before the PSV-2018-05xx security fixes above —
useful as a reference point against the public CVE-2019-20699 /
CVE-2017-18862-class advisories discussed in
[`../../docs/research.md`](../../docs/research.md). 1.6.0.25 is current and
is what the device should actually run.

**Important caveat for later probing/flashing:** per NETGEAR's own 1.6.0.15
and 1.6.0.25 release notes, **NSDP discovery was removed starting with
firmware 1.6.0.15** — the switch stops responding to the classic NSDP
broadcast query, and NETGEAR's guidance shifts to the newer "NETGEAR
Discovery Tool" (UPnP-based) or the NETGEAR Insight app. If the physical
switch is still on older firmware (anything before 1.6.0.15), the NSDP probe
in `tools/nsdp_discover.py` should work; on 1.6.0.15+ it may see nothing even
though the switch is alive on the LAN. This needs confirming against the
actual unit once it is reachable.

## Intermediate release history (from NETGEAR KB, not all downloaded)

1.3.0.3, 1.4.0.2, 1.4.0.9, 1.5.0.4, 1.5.0.5, 1.6.0.3, 1.6.0.4, 1.6.0.6,
1.6.0.10, 1.6.0.11, 1.6.0.15 (NSDP removed), 1.6.0.21, 1.6.0.24, 1.6.0.25.
Each has its own `kb.netgear.com` article; see `../../docs/research.md` for
the ones relevant to security history.
