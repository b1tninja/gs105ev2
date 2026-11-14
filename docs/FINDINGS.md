# GS105Ev2 deep-dive — consolidated findings

A capstone summary of what this project has established about the NETGEAR
GS105Ev2, with pointers to the detailed docs. Scope and legal framing are in
[`../LEGAL.md`](../LEGAL.md); everything here concerns a switch the author
owns, for configuring/auditing it and for understanding what it runs.

**Overall status:** desk research, firmware analysis, a working management
library, and a VLAN plan are done. The physical switch is **not yet connected**
(no NSDP reply on the LAN as of 2026-11-13), so all live-device behavior and
every config *write* remain unverified against hardware.

## 1. Device & silicon — [`GS105Ev2.md`](GS105Ev2.md), [`HARDWARE.md`](HARDWARE.md)

- **NETGEAR GS105Ev2**, 5-port gigabit "Smart Managed Plus"/ProSAFE Plus
  switch. 802.1Q VLANs (tagged/untagged + per-port PVID), port-based VLANs,
  web UI + NSDP management.
- **Switch SoC: Realtek RTL8367N** — confirmed from firmware strings and
  corroborated by the chip's own datasheet (single-chip 5-port 10/100/1000M
  controller, QFN-88).
- **Management CPU: an 8051 core *on-die* in the RTL8367N** — confirmed two
  ways: Ghidra disassembled the firmware's reset vector into a clean 8051
  instruction stream, and the datasheet documents an embedded 8051 (16 KB code
  memory, 48 KB data RAM, **code banking**, boots from external SPI flash).
- **No FCC ID exists** for this model (radio-less device → Part 15 Subpart B
  SDoC, no type-approval grant); the only regulatory doc is NETGEAR's EU DoC.
  A physical teardown is the only route to internal photos / a flash dump.

## 2. Firmware — [`FIRMWARE-FORMAT.md`](FIRMWARE-FORMAT.md), [`GHIDRA-NOTES.md`](GHIDRA-NOTES.md)

- **Container header decoded** (from an 8-version corpus diff): a 20-byte
  header — magic `0x87654321`, big-endian payload length (`= file_size − 20`,
  verified across all 8 versions), a fixed `0x332255ff` marker, and two
  still-unidentified 4-byte fields. Parser: [`../tools/fw_header.py`](../tools/fw_header.py).
- **Code-banking layout confirmed (32 KiB banks):** lower 32 KiB common, upper
  32 KiB banked; bank *N* = flash offset `0x8000 + N·0x8000` mapped at logical
  `0x8000`. Proven by carving a `common + bank N` image and re-importing — web
  strings land at predicted logical addresses and common C-startup code copies
  bank data from them. This makes any single bank analyzable.
- **NSDP discovery is removed in firmware 1.6.0.25:** the `"NSDP"` signature
  appears **0 times** in the 682 KiB image — a hardware-independent
  confirmation of NETGEAR's "removed on 1.6.0.15+" note. The web UI (not NSDP)
  is the management path on current firmware.
- **Software stack:** a custom Realtek SDK — an in-house httpd
  (`common/src/app/web/httpd.c`) and a TCP/IP stack called "lwps", plus
  embedded PNGs and 11 gzip'd web-UI assets past flash `~0x57000`.
- **The full web UI CGI/page table recovered from bank 2** (34+ endpoints,
  including `factory_default.cgi`, `device_reboot.cgi`, `loader_upg.cgi`/
  `fwug.cgi`, `backup_conf.cgi`/`restore_conf.cgi`, `switch_discovery.cgi`) —
  a direct, firmware-sourced attack-surface inventory for the web management
  interface, not inferred by probing. See "Round 7" in
  [`GHIDRA-NOTES.md`](GHIDRA-NOTES.md).
- **Open (deliberately stopped here):** tracing the httpd request dispatcher
  that walks the CGI table above to route a request — the bank-carve method
  makes it possible, and Round 7 narrowed the search (ruled out one
  candidate routine, which turned out to be a TCP-state-name formatter, not
  the dispatcher), but wiring the cross-bank call graph is a large further
  effort with little practical payoff (the device isn't present and the
  management goals are met).

## 3. Management protocol & library — [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md), [`LIBRARY.md`](LIBRARY.md), [`WEBUI-AUTH.md`](WEBUI-AUTH.md)

- **NSDP** (UDP 63321-63324) packet/TLV format documented and reimplemented as
  the stdlib-only **`gs105ev2`** Python package: discovery, status, version,
  port speeds, 802.1Q + port-based VLANs, PVIDs, port stats, QoS/IGMP/
  bandwidth/mirror. Reads are safe; **writes are gated** (`allow_write=True` +
  password) and **hardware-unverified**. 16 deterministic wire-format tests.
- **Web UI login** hashes `MD5(interleave(password, rand))` client-side over
  **plain HTTP** — a weak, replayable-on-LAN scheme, not transport security.

## 4. Security posture — [`SECURITY-ANALYSIS.md`](SECURITY-ANALYSIS.md), [`research.md`](research.md)

- All vendor-acknowledged CVEs/advisories (CVE-2017-18862, CVE-2019-20699 /
  PSV-2018-0538, PSV-2018-0542, PSV-2018-0612, the 2016 Westermann cluster)
  are **fixed by firmware 1.6.0.25** — so update to it before trusting the unit.
- The **management plane is weak by design** and cannot be patched away (plain
  HTTP, client-side-only password hashing, historically weak NSDP auth). The
  realistic attacker is anyone on the same L2 broadcast domain.
- **Treat the switch as a VLAN tagger, not a security boundary.** Keep its
  management interface on a trusted VLAN only, never on an untrusted/personal
  segment or the internet.

## 5. VLAN isolation plan — [`VLAN-PLAN.md`](VLAN-PLAN.md)

- Goal: isolate a work computer from personal devices. Design: two VLANs
  (work/personal) with a tagged trunk to **`router`** (the inline Arch bridge),
  which does the L3 routing + firewalling — the ISP gateway can't firewall
  intra-LAN, so the switch alone can't enforce isolation.
- Switch side is scriptable/auditable with the `gs105ev2` library once connected.
- **Blocked on infra answers** (coordinated with the infra session):
  physical insertion point, whether router becomes the VLAN enforcer, the
  host→VLAN map, addressing, and the 5-port budget. See the shared coordination
  note.

## What's done vs. open

| Area | State |
| --- | --- |
| Legal framing, provenance, hashed firmware | Done |
| Chipset + CPU identification | Done (confirmed) |
| Firmware container + bank layout | Done (decoded/confirmed) |
| `gs105ev2` library (reads) | Done, unit-tested; live reads unverified |
| `gs105ev2` library (writes) | Implemented, **gated + hardware-unverified** |
| Security analysis | Done |
| VLAN plan | Drafted; **waiting on infra answers** |
| Httpd/CGI handler trace | **Open**; CGI/page table recovered (Round 7), dispatcher itself still untraced |
| Physical teardown / flash dump | **Not started** (device not in hand) |
