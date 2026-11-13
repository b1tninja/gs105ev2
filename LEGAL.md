# Legal notice

**This is not legal advice.** Laws vary by jurisdiction. Consult a qualified
attorney before relying on this document for your own risk assessment.

## Independent, unofficial tool

`gs105e-switch` is an independent open-source research project. It is **not
affiliated with, endorsed by, sponsored by, or approved by** NETGEAR, Inc. or
any related entity.

References to "NETGEAR", product model names (for example "GS105Ev2",
"ProSAFE", "Smart Managed Plus"), and similar marks are **nominative fair
use** — used only to identify compatible hardware and the vendor's publicly
reachable support/download endpoints. Those marks remain the property of
their respective owners.

## Purpose

This repository documents and tools around a **NETGEAR GS105Ev2 ("Smart
Managed Plus"/ProSAFE Plus) switch owned by the author**, for:

- configuring and auditing the switch as part of segmenting a home network
  with VLANs;
- understanding the device's management protocol (NSDP, UDP ports
  63321-63324) and web UI well enough to use and secure it;
- general curiosity about what the device runs, informed by the vendor's own
  published firmware and by prior public security research (see
  [`docs/research.md`](docs/research.md));
- interoperability with a device the user lawfully possesses.

## What this repository does **not** contain

This repository is **tooling and notes only**. It must not contain, and
contributors must not add:

- redistributed copies of NETGEAR firmware images, beyond what is needed
  locally for the author's own device (kept untracked — see `.gitignore`);
- NETGEAR's own configuration utilities, installers, or extracted installer
  resources, beyond the author's local, untracked copy;
- manuals, PDFs, or other copyrighted vendor documentation;
- decompiled or disassembled copies of vendor programs, beyond short,
  clearly-labeled excerpts used to document an interoperability fact (a
  string table entry, a protocol constant) and never full reassembled
  source;
- packet captures that embed copyrighted payloads beyond what is needed to
  document the discovery/management protocol itself;
- credentials, serials harvested from third parties, or API secrets.

Downloaded firmware and utilities are written only to the user's local
machine (paths ignored by `.gitignore`, same as the `downloads/` pattern used
in the sibling `mfc9330cdw` and `brother-firmware` projects) and are **not
redistributed** by this project. Only hashes, source URLs, and factual
version/changelog notes are committed.

Protocol facts documented here (NSDP header layout, TLV type codes, UDP
ports, web UI endpoint paths) are **factual interface observations** needed
for interoperability and for auditing the author's own device, not copies of
vendor source code. Where those facts come from prior public research (the
2016 Westermann disclosure, the Wikipedia NSDP page, `ProSafeLinux`,
`ngadmin`), they are cited rather than re-derived in secret, and this
project's own write-ups are independently written.

## Reverse engineering & DMCA context (U.S.)

Analysis in this project is undertaken to achieve **interoperability** with,
and to **security-audit**, a device the author lawfully possesses, as part of
a home-network segmentation project.

Relevant U.S. provisions often discussed in this context include:

- **17 U.S.C. § 1201(f)** — limited exception permitting circumvention and
  information sharing solely for identifying and analyzing program elements
  necessary to achieve interoperability of an independently created computer
  program, subject to statutory conditions;
- **17 U.S.C. § 1201(j)** — limited exception for good-faith **security
  testing** of a computer, computer system, or computer network, with the
  owner's authorization (here, the author's own switch and LAN);
- **17 U.S.C. § 107** — fair use (fact-specific);
- the Library of Congress's recurring **DMCA § 1201 rulemaking exemptions**
  for good-faith security research on lawfully-acquired devices (37 CFR
  201.40), which have repeatedly covered consumer network devices;
- case law recognizing reverse engineering for compatibility in appropriate
  circumstances (for example *Sega v. Accolade*, *Sony v. Connectix*).

Comparable interoperability provisions exist elsewhere (for example EU
Directive 2009/24/EC Art. 6). **These exceptions are narrow.** Meeting some
factors does not automatically make every use lawful.

This project:

- does **not** aim to bypass subscription, authentication, or DRM paywalls;
- does **not** redistribute vendor copyrighted works;
- does **not** provide cracked keys, patched vendor binaries, or tools whose
  primary purpose is copyright infringement;
- probes and configures only the author's own device, on the author's own
  LAN (see [`SECURITY.md`](SECURITY.md) and the scope note in each probe
  script);
- talks to the same publicly reachable NSDP/web-UI/update mechanisms the
  vendor's own utilities use, using independently reimplemented
  request/response handling or well-cited prior public research.

## Security research

Discovery and configuration probes in this repository are **read-only by
default** and scoped to the author's own LAN (see [`SECURITY.md`](SECURITY.md)
for the exact boundary). Any probe that writes to the device, changes
configuration, or touches firmware is treated as a separate, explicitly
scoped step, not run casually, and is not part of this initial deep-dive.

Good-faith security research norms (responsible disclosure, lawful device
access, no enabling third-party infringement) are followed throughout. See
also the EFF [Coders' Rights Project Reverse Engineering
FAQ](https://www.eff.org/issues/coders/reverse-engineering-faq).

## GitHub DMCA process

If a copyright owner believes material on GitHub infringes, they may file a
DMCA takedown notice under GitHub's
[DMCA Takedown Policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy).
Maintainers may respond with a **counter notice** when there is a good-faith
belief the material was disabled by mistake or misidentification. See
[`DMCA.md`](DMCA.md) for the elements GitHub requires and how this project
positions itself.

## No warranty; your responsibility

Software and notes are provided **AS IS** under the MIT License (`LICENSE`).
Flashing firmware, or writing configuration via NSDP, can brick or lock out
the switch. You are responsible for complying with applicable law, license
terms that bind you, and safe update practices.
