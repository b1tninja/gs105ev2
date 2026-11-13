# Public research survey — NETGEAR GS105E/GS108E "Plus"/ProSAFE smart switches

Summarized, with links, rather than reproduced. If you need primary-source
detail, follow the links — don't rely solely on this summary.

## Security advisories & disclosures

- **Benedikt Westermann, "Multiple Vulnerabilities — Netgear GS105Ev2"**
  (Full Disclosure, 27 Jan 2016):
  <https://seclists.org/fulldisclosure/2016/Jan/77> (mirrored at
  <https://seclists.org/bugtraq/2016/Jan/147>,
  <https://packetstormsecurity.com/files/135480/>). Reported against firmware
  1.3.0.3/1.4.0.2: an **NSDP authentication bypass** (write operations,
  including firmware flash, with no valid credentials), weak XOR-based
  password obfuscation plus plaintext broadcast of the (obfuscated) password
  by NETGEAR's own configuration utility, reflected XSS in
  `switch_info.cgi`, no CSRF protection, plaintext password in config
  backups (fixed in 1.4.0.2), and predictable/reused session IDs tied to
  uptime. Disclosed after NETGEAR confirmed the findings (Aug 2015) but said
  it had no immediate fix plan (Sep 2015). References CVE-2014-4864 as
  describing a related NSDP issue. CVSSv2 8.3.
- **NETGEAR PSV-2015-0043 — "Authentication Bypass on ProSAFE Web Managed
  Switches"**: <https://kb.netgear.com/000037849/>. Vendor advisory
  responding to the class of issue above; affected model list includes
  GS105Ev2, GS105PE, GS108Ev3, GS108PEv3, GS116Ev2, JGS516PE, JGS524Ev2,
  JGS524PE, GSS108E, GSS116E, XS708Ev2, XS716E. Fix: update firmware; no CVE
  assigned in the advisory itself.
- **NETGEAR PSV-2018-0538 — "Pre-Authentication Buffer Overflow on Some
  Switches"**: <https://kb.netgear.com/000061230/>. Fixed in GS105Ev2
  firmware 1.6.0.4. Tracked externally as **CVE-2019-20699** (listed with a
  9.8 CVSS score by third-party aggregators, i.e. unauthenticated/
  network-reachable).
- **NETGEAR PSV-2018-0542 — "Missing Function Level Access Control on Some
  Switches"**: <https://kb.netgear.com/000061463/>. Fixed in 1.6.0.4.
- **NETGEAR PSV-2018-0612 — "Sensitive Information Disclosure on Some
  Switches"**: <https://kb.netgear.com/000061481/>. Fixed in 1.6.0.4.
- Third-party CVE aggregation for this firmware line: **CVE-2017-18862**
  (authentication bypass, same family as the 2016 disclosure) and
  **CVE-2019-20699** above — see
  <https://cyber.vumetric.com/vulns/netgear/gs105e-firmware/> and
  <https://cpe.gcve.eu/products/d4e3ae29-e22a-5da4-89e1-9c3a9a7a6740> for the
  CPE/CVE cross-reference (not independently verified here, since these are
  third-party aggregators, not NETGEAR or MITRE directly).

**Takeaway for this project:** firmware **before 1.6.0.4** has multiple
NETGEAR-acknowledged holes, several network-reachable pre-auth. The switch
should be updated to **1.6.0.25** (current, see
`../downloads/firmware/README.md`) before being trusted on a segmented
network, and the NSDP auth-bypass history is a reason to keep NSDP traffic
confined to a trusted VLAN/broadcast domain even after patching.

## Protocol reverse-engineering (prior art)

- **Wikipedia — "Netgear Switch Discovery Protocol"**:
  <https://en.wikipedia.org/wiki/Netgear_Switch_Discovery_Protocol>. Packet
  header/TLV layout (used as the basis for
  [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md)); flags its own citations as
  incomplete.
- **ProSafeLinux** (`psl-cli.py`, Python): a CLI client for querying/setting
  NSDP data on GS105E/GS108E-class switches.
  <https://gh.r-mj.com/Z3po/ProSafeLinux> (mirror host; verify against the
  canonical upstream before relying on provenance). Notes the "Web browser
  only" switch-management-mode setting as a case where NSDP discovery stops
  responding — directly relevant to the 1.6.0.15+ NSDP-removal behavior
  NETGEAR itself later shipped.
- **ngadmin** (C): Linux admin utility for GS105E/GS108E-class switches.
  <https://github.com/Alkorin/ngadmin>.
- **python-netgear-switch-library**: broader library covering SNMP, NSDP,
  HTTP web UI, and FASTPATH CLI across several NETGEAR switch families.
  <https://python-netgear-switch-library.readthedocs.io/>. Describes NSDP as
  an "undocumented UDP protocol", consistent with the above.
- **py-netgear-plus**: Python library driving some of these switches (GS105E/
  GS108E listed as tested) over the **web UI** rather than NSDP.
  <https://pypi.org/project/py-netgear-plus/>.

## Vendor tooling naming history

- Older NETGEAR material: **"ProSAFE Plus Configuration Utility"** (PCU),
  Windows-only, sometimes referred to as "Smart Control Center" in even
  older documentation. Required version climbed with firmware (>= V2.4.3 for
  firmware >= 1.5.0.4; >= V2.7.2 for firmware >= 1.6.0.3).
- Current: **NETGEAR Discovery Tool (NDT)**, v2.0.4 as of this writing,
  Windows/macOS/Linux, supporting both UPnP and (on older firmware) NSDP.
  <https://kb.netgear.com/000066269/>.
- NETGEAR's own 1.6.0.15/1.6.0.24/1.6.0.25 release notes direct users to NDT
  or the **NETGEAR Insight** app once NSDP discovery is gone from the
  switch's side.

## Hardware / teardown

**Update:** the chipset question below is now resolved directly from the
firmware itself — see [`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md). Both
mirrored firmware images contain the plaintext string `RTL8367N` (plus one
`RTL8367B` reference), confirming a **Realtek RTL8367N** switch SoC without
needing a physical teardown. The comparable-product survey below was the
working hypothesis before that was found; it's kept for context since it
turned out to be the right family.

No teardown specific to the GS105Ev2 was found. For context, comparable
consumer-class unmanaged/smart switches use Realtek switch SoCs:

- NETGEAR GS208 and Cisco SG110D-08 teardowns both report a Realtek
  **RTL8370N**-class chip (hobbyist teardown, hackaday.io project logs,
  e.g. <https://hackaday.io/project/170181/log/175870-04112020>).
- NETGEAR GS108Tv3 (managed, different product tier) uses an **RTL8380M**
  SoC (<https://svanheule.net/switches/gs108tv3>).
- TP-Link TL-SG105S-M2 (different vendor, same size class) also uses a
  Realtek switch chip per ServeTheHome's review.

**Now confirmed for the GS105Ev2 itself** via firmware strings (RTL8367N),
not just inferred from comparable products — see above. No FCC ID was
located for this model via search; the only regulatory document found was
NETGEAR's EU Declaration of Conformity
(`204-11412-06_CE_GS105Ev2_EN-EP-FR-IT-GR-SP_20May25.pdf`), which does not
include an FCC ID or internal photos, so a physical/visual cross-check is
still open if it matters later.

## What this means for realistic next steps

- Firmware unpacking is realistic and underway — see
  [`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md): the RTL8367N chipset is
  confirmed from firmware strings, the 20-byte vendor header is decoded
  (magic + payload length, two fields still unidentified) from an 8-version
  corpus diff, 11 gzip-compressed web-UI assets were extracted with real
  binwalk (`cargo install binwalk`, since the PyPI `binwalk` package is a
  non-functional legacy stub), and the login page's client-side password
  scheme is documented in [`WEBUI-AUTH.md`](WEBUI-AUTH.md). Remaining work:
  confirm the CPU core (8051 is the current working hypothesis) and
  disassemble the executable region — a job for `ghidra-mcp`, not yet
  attempted.
- Live protocol probing (NSDP discovery, web UI fingerprinting) does **not**
  require the chipset to be known and is the right first physical-device
  step — see [`../tools/nsdp_discover.py`](../tools/nsdp_discover.py).
- The known auth-bypass/overflow history is a strong argument for (a)
  confirming current firmware is >= 1.6.0.4 (ideally 1.6.0.25) before
  trusting the device, and (b) not exposing its management plane (NSDP, web
  UI) outside the intended management VLAN.
