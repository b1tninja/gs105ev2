# Security analysis — NETGEAR GS105Ev2 on a segmented home LAN

A consolidated threat assessment for the owner of this switch, who intends to use
it to separate a work computer from personal devices with VLANs. It pulls together
[`research.md`](research.md) (advisory survey), [`WEBUI-AUTH.md`](WEBUI-AUTH.md)
(login scheme) and [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md) (management protocol),
and adds a threat model and hardening list. Scope is defensive and limited to the
author's own device and LAN; see [`../SECURITY.md`](../SECURITY.md) and
[`../LEGAL.md`](../LEGAL.md).

**Bottom line.** On firmware 1.6.0.25 the known, vendor-acknowledged
vulnerabilities for this model are patched. The *design* of the management plane
(plain HTTP, client-side MD5 "challenge", a weak historical NSDP) is not, and
cannot be patched away. Treat the switch as a convenient VLAN tagger, not as a
security boundary, and keep its management interface off any segment you do not
trust.

Evidence labels used below: **[vendor]** read from the NETGEAR KB article on
2026-11-13; **[aggregator]** from NVD or third-party CVE mirrors; **[inferred]**
our reasoning, not a published statement; **[unverified]** not checked on this
project's own hardware.

## 1. Known vulnerabilities

| ID | What | Affected (GS105Ev2) | Fixed in | 1.6.0.25 past the fix? |
| --- | --- | --- | --- | --- |
| **CVE-2017-18862** | NSDP improper authentication (auth bypass, same family as the 2016 disclosure). NVD CVSS v3.1 6.5 [aggregator] | Firmware dated before 2017-05-11 [aggregator]. NVD gives a date, not a firmware number | No firmware number published in the sources checked. [inferred] any release after the 2017 date, so 1.6.0.4 or later | Yes [inferred]. 1.6.0.25 is later than every release the advisories below name as a fix |
| **CVE-2019-20699** / **PSV-2018-0538** | Pre-authentication buffer overflow. KB: published 2019-09-05, CVSS v3.0 7.5, vector `AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H` (availability), KB labels it "Medium" and lists no CVE. NVD: 9.8 critical, published 2020-04-16 | Before 1.6.0.4 [vendor] | **1.6.0.4** [vendor] | Yes |
| **PSV-2018-0542** | Missing function-level access control. KB: CVSS v3.0 6.0 (`AV:L/PR:H`), no CVE, published 2019-12-04 | Before 1.6.0.4 [vendor] | **1.6.0.4** [vendor] | Yes |
| **PSV-2018-0612** | Sensitive information disclosure. KB: CVSS v3.0 5.4 (`AV:A/PR:N/C:L/I:L`), no CVE, published 2019-12-04 | Before 1.6.0.4 [vendor] | **1.6.0.4** [vendor] | Yes |
| **2016 Westermann cluster** (NSDP auth bypass incl. firmware flash; XOR-obfuscated password broadcast; reflected XSS in `switch_info.cgi`; no CSRF protection; predictable session IDs; plaintext password in config backup) | Reported against 1.3.0.3 / 1.4.0.2 [disclosure](https://seclists.org/fulldisclosure/2016/Jan/77) | Config-backup password: **1.4.0.2** per the disclosure. Remaining items: [PSV-2015-0043](https://kb.netgear.com/000037849/) says only "firmware fixes are currently available" and gives no version or CVE | Unclear per item. See notes |

Sources: [PSV-2018-0538](https://kb.netgear.com/000061230/),
[PSV-2018-0542](https://kb.netgear.com/000061463/),
[PSV-2018-0612](https://kb.netgear.com/000061481/),
[PSV-2015-0043](https://kb.netgear.com/000037849/),
[NVD CVE-2019-20699](https://nvd.nist.gov/vuln/detail/CVE-2019-20699),
[CVE-2017-18862 summary](https://avd.aquasec.com/nvd/2017/cve-2017-18862),
[Westermann disclosure](https://seclists.org/fulldisclosure/2016/Jan/77).

Notes and caveats:

- **Severity disagreement.** [`research.md`](research.md) quotes 9.8 for
  CVE-2019-20699 from aggregators. NETGEAR's own KB scores the same advisory 7.5
  with an availability-only vector, and says no CVE applies. NVD's 9.8 appears to
  come from a different scoring of the same bug. Both are network-reachable and
  pre-authentication, which is what matters here. We do not know which is
  "right", and the memory-corruption class means code execution should not be
  ruled out. [inferred]
- **CVE-2017-18862 has no firmware-number fix.** NVD expresses the affected range
  as a date. We could not find NETGEAR text mapping it to a version. The
  conclusion that 1.6.0.25 is past it rests on date ordering, not on a vendor
  statement.
- **The 2016 cluster is the weakest-documented row.** NETGEAR's PSV-2015-0043
  covers the auth-bypass class and names GS105Ev2 but gives no version. We have
  not confirmed per-item (XSS, CSRF, session ID) fixes. Whether CSRF protection
  or session-ID randomness were ever genuinely redesigned is **[unverified]**;
  see section 2 for why we do not assume so.
- **The KB pages say "prior to the listed version", so 1.6.0.4 is the floor.**
  This agrees with [`research.md`](research.md). The current firmware is
  1.6.0.25 (see `../downloads/firmware/README.md`).
- **No patch history is a guarantee.** Absence of a published advisory after
  1.6.0.4 means nothing was disclosed, not that nothing is there. The device is
  an 8051-class management CPU running a closed firmware image
  ([`GHIDRA-NOTES.md`](GHIDRA-NOTES.md)), and this class of device has a poor
  disclosure record.

## 2. Management-plane weaknesses that persist at any patch level

These are properties of the design, not bugs awaiting a fix.

1. **Plain-HTTP web UI.** There is no TLS. Anything on the path, and anything on
   the same broadcast domain that can observe or inject traffic, sees and can
   alter the whole session. NETGEAR documents the UI as HTTP for this switch
   family ([`WEBUI-AUTH.md`](WEBUI-AUTH.md)).
2. **Client-side-only password "protection".** The login page interleaves the
   password with a server-supplied `rand` value and sends `md5()` of the result.
   That is not a cryptographic challenge-response: MD5 is fast, so a captured
   `(rand, hash)` pair can be attacked offline, and a captured hash is
   directly usable against a `rand` that is still valid. Whether `rand` is
   single-use and unpredictable is **[unverified]** against the live device
   ([`WEBUI-AUTH.md`](WEBUI-AUTH.md), "Open question"). Short or dictionary
   passwords fall quickly.
3. **No evidence of modern hardening.** Nothing in the extracted firmware or the
   documents suggests login rate limiting, lockout, CSRF tokens, HTTPS, secure
   cookie handling, or an access-control list for management sources. These are
   absence-of-evidence observations from limited analysis, not confirmed
   absences.
4. **NSDP's history.** NSDP is an unauthenticated-by-design UDP broadcast
   protocol (ports 63321-63324) whose authentication was bypassable in 2016 and
   whose password field was only XOR-obfuscated
   ([`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md)). NETGEAR removed NSDP discovery from
   firmware 1.6.0.15 onward (per its own release notes; **[unverified]** on this
   hardware). That reduces the attack surface but does not tell us whether the
   NSDP *write* path is also gone. Do not assume it is.
5. **Single shared admin credential, no accounts.** One password guards
   everything, and it travels over the scheme in item 2.

**Realistic attacker.** Everything above is exploitable only by someone who can
reach the management IP or see its traffic, which in practice means being on the
**same layer-2 broadcast domain** (NSDP broadcasts, sniffing, ARP spoofing) or
anywhere that can route to the management address. This is not a switch that
anyone reaches from the internet unless it is port-forwarded, which must never
happen. The attacker is therefore a compromised or hostile device on the LAN:
an IoT gadget, a guest's laptop, a malware-infected personal machine.

## 3. Threat model for this deployment

**Goal:** work computer isolated from personal devices.
**Assumed adversary:** malware or a person on the *personal* segment. This is the
realistic case, since personal devices (phones, consoles, smart TVs, guests) are
the less-trusted side.

What an attacker on the personal segment can do depends on where the switch's
management address lives.

- **If management is reachable from the personal segment** (for example, it keeps
  the default untagged VLAN 1 and the personal devices are there too), the
  attacker can attempt every item in section 2: sniff or replay a login, brute
  force the MD5 password, and exploit any unpatched or undiscovered pre-auth
  bug. A successful takeover lets them **edit the VLAN table**: add the personal
  port to the work VLAN, change PVIDs, enable port mirroring of the work port, or
  reset to factory defaults. Any of these ends isolation, and port mirroring does
  so silently. This is the main risk, and it is the reason for confinement.
- **If management is on a trusted VLAN the personal segment cannot reach**, the
  attack surface for that attacker shrinks to the switch's data-plane behavior
  (VLAN-tag handling) and whatever is exposed by misconfiguration.
- **VLAN hopping.** Classic double-tagging works when an attacker-facing access
  port shares a native VLAN with a trunk. A small smart switch's tag handling has
  not been tested by this project **[unverified]**. Keep the PVID of every
  trunk-adjacent port off any VLAN used by an untrusted host, and do not carry
  VLAN 1 (default) as an untagged native on trunks. Also remember a
  smart-switch firmware bug could leak frames across VLANs and no one outside
  NETGEAR can easily audit that.
- **Never reachable from the internet.** No port forwards, no UPnP mappings to
  the switch, no remote-management feature enabled.

**Why switch VLANs alone are not enough.** A VLAN is a layer-2 separation. It
says nothing about routing. Whatever router or L3 device joins the VLANs decides
what talks to what, and that is where policy belongs (a firewall with a default
deny between the personal and work networks). The switch's own isolation depends
on a management plane that this document shows to be weak, so a management
compromise, a VLAN-handling bug, or a mistaken membership change collapses the
separation with no second barrier to stop it. Defense in depth means the work
machine should still be safe if the switch is fully owned: host firewall on,
TLS/VPN for work traffic, no trust in the local network.

Honest limits of this analysis: no live testing, no confirmation of `rand`
quality, NSDP write behavior on 1.6.0.25, or VLAN-hopping behavior has been done
on the owner's unit.

## 4. Hardening recommendations

1. **Update to 1.6.0.25 first**, before putting the switch between any two
   segments, while it is still on a network you trust. Get the image from
   NETGEAR's download page only and compare against the hashes recorded in
   `../downloads/firmware/README.md`. This clears every vendor-acknowledged issue
   in section 1. Do the update over a wired connection, and have a recovery plan,
   since a failed flash can brick it ([`../LEGAL.md`](../LEGAL.md)).
2. **Set a long, unique admin password** (a password-manager passphrase of 20+
   characters). Given the MD5 scheme, length is the only thing slowing offline
   attack. Never reuse it anywhere else, since it is exposed to anyone who can
   sniff the login.
3. **Disable unused management modes.** Use the switch's management-mode setting
   to restrict it to web-only where available (this also silences NSDP on older
   firmware, per the ProSafeLinux note in [`research.md`](research.md)). Disable
   the NETGEAR Insight/cloud features, remote management and any
   SNMP/Telnet equivalents if present. Confirm in the UI what is enabled; we have
   not verified the menu on 1.6.0.25.
4. **Put the management IP on a dedicated trusted VLAN only** (a small
   "management" VLAN that contains the switch and one admin port or your admin
   machine). Move the switch's management VLAN away from VLAN 1 and make sure no
   port facing a personal or guest device carries it. Do not mix it with the
   work VLAN unless you accept that work devices can attack it.
5. **Firewall at layer 3.** Block personal and guest networks from the switch's
   management IP, and block both from reaching each other except what is needed,
   on the router or firewall. Ensure the switch has no route to the internet if
   you do not need it (no default gateway on the switch, or block it
   outbound).
6. **Do not rely on the switch as the only isolation boundary.** Keep host
   firewalls enabled on the work computer, use a VPN or TLS for work traffic,
   and treat the local network as hostile. If the threat to the work machine
   matters, use a separate physical switch or router interface for it.
7. **VLAN hygiene.** Use explicit PVIDs on every port; avoid VLAN 1 for anything
   in use; do not run tagged trunks to untrusted devices; leave unused ports
   in a dead-end VLAN with no members; disable port mirroring unless you are
   actively using it.
8. **Administer deliberately.** Log in only from the admin port, only when
   needed, and log out. Do not browse other sites in the same browser session
   (the 2016 disclosure reported no CSRF protection, and its status is
   unconfirmed, see section 1). Prefer a wired direct connection for password
   changes.
9. **Monitor.** Keep a record of the VLAN table, PVIDs and mirror settings
   (export a config backup and store it securely; note that older firmware
   stored the password in plaintext in backups, fixed by 1.4.0.2 per the
   disclosure, so inspect the file before sharing it). Re-check the settings
   periodically for drift. Watch the router for unexpected traffic to the switch
   address and for new MAC addresses on the work VLAN. Check NETGEAR's security
   advisories page and this repository's [`research.md`](research.md) for new
   entries, and re-run the read-only discovery tool
   ([`../tools/nsdp_discover.py`](../tools/nsdp_discover.py)) after updates to
   see what the switch answers to.
10. **Verify the claims here on the real unit.** Items marked **[unverified]**
    (is NSDP truly silent on 1.6.0.25, is `rand` fresh per load, is a management
    VLAN other than 1 supported and enforced) can be checked read-only from the
    admin port. Those checks are listed as open questions in
    [`WEBUI-AUTH.md`](WEBUI-AUTH.md) and [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md).

## Sources

- [NETGEAR PSV-2018-0538 (KB 000061230)](https://kb.netgear.com/000061230/)
- [NETGEAR PSV-2018-0542 (KB 000061463)](https://kb.netgear.com/000061463/)
- [NETGEAR PSV-2018-0612 (KB 000061481)](https://kb.netgear.com/000061481/)
- [NETGEAR PSV-2015-0043 (KB 000037849)](https://kb.netgear.com/000037849/)
- [NVD: CVE-2019-20699](https://nvd.nist.gov/vuln/detail/CVE-2019-20699)
- [CVE-2017-18862 mirror (Aqua AVD)](https://avd.aquasec.com/nvd/2017/cve-2017-18862)
- [Westermann, Full Disclosure, 2016-01-27](https://seclists.org/fulldisclosure/2016/Jan/77)
- Project docs: [`research.md`](research.md), [`WEBUI-AUTH.md`](WEBUI-AUTH.md),
  [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md), [`../SECURITY.md`](../SECURITY.md),
  [`../LEGAL.md`](../LEGAL.md)
