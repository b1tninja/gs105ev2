# NSDP (NETGEAR Switch Discovery Protocol) — notes

Summarized from public sources (Wikipedia, the 2016 Westermann disclosure,
and the `ProSafeLinux`/`ngadmin` open-source clients) and cited rather than
re-derived; see [`research.md`](research.md) for links. These are
**factual protocol observations**, used here for interoperability and
auditing the author's own switch — see [`../LEGAL.md`](../LEGAL.md).

Treat the TLV type table as **incomplete** — the upstream sources themselves
flag it as such, and it has not been independently verified against this
project's own hardware yet.

## Transport

- UDP, broadcast to `255.255.255.255` (or a specific device IP once known).
- Ports 63321-63324. The common discovery flow sends a request from the
  client's 63321/63323 to the switch's 63322/63324.
- Stateless, single-packet request/response.

## Packet layout

All offsets in hex, from the start of the UDP payload:

| Offset | Length | Field |
| --- | --- | --- |
| `0x00` | 1 | Protocol version (`0x01`) |
| `0x01` | 1 | Opcode: `0x01` read request, `0x02` read response, `0x03` write request, `0x04` write response |
| `0x02` | 2 | Operation result / status |
| `0x04` | 4 | Unknown/reserved |
| `0x08` | 6 | Host (client) MAC address |
| `0x0E` | 6 | Device (switch) MAC address — `00:00:00:00:00:00` acts as "any"/broadcast target |
| `0x14` | 2 | Unknown/reserved |
| `0x16` | 2 | Sequence number, increments per request |
| `0x18` | 4 | Signature, ASCII `"NSDP"` (`0x4E 0x53 0x44 0x50`) |
| `0x1C` | 4 | Unknown/reserved |
| `0x20` | N | Body: sequence of TLV records |
| `0x20+N` | 4 | End-of-message marker `0xFFFF0000` |

Body TLV record: 2-byte type, 2-byte length, then `length` bytes of value.

## TLV types (incomplete)

| Type | Meaning |
| --- | --- |
| `0x0001` | Device model |
| `0x0003` | Device name |
| `0x0004` | Device MAC address |
| `0x0005` | System location |
| `0x0006` | Current IP address |
| `0x0007` | IP network mask |
| `0x0008` | Router/gateway IP address |
| `0x0009` | Admin password (write) |
| `0x000a` | Admin password (read-related) |
| `0x000b` | DHCP mode: `0`=static, `1`=DHCP, `2`=refresh DHCP |
| `0x000d` | Firmware version, slot 1 |
| `0x000e` | Firmware version, slot 2 |
| `0x000f` | Active firmware slot after reboot |
| `0x0013` | Reboot (write-only action) |
| `0x0400` | Factory reset (write-only action) |
| `0x0c00` | Port speed/link status: `port`,`speed` (speed `0`=down, `1`=10H, `2`=10F, `3`=100H, `4`=100F, `5`=1G) |
| `0x1000` | Port traffic statistics: `port` + 6× uint64 counters (rx, tx, pkts, bcast, mcast, errors) |
| `0x1400` | Reset port statistics (write-only action) |
| `0x2000` | VLAN engine / which VLAN mode is enabled |
| `0x2400` | Port-based VLAN membership: `vlan_id`(2) + `port_mask`(1) |
| `0x2800` | **802.1Q** VLAN membership: `vlan_id`(2) + `tagged_mask`(1) + `untagged_mask`(1) |
| `0x2c00` | VLAN delete (write) |
| `0x3000` | Per-port PVID (default VLAN): `port`(1) + `vlan_id`(2) |
| `0x3400` | QoS mode |
| `0x3800` | Port-based QoS |
| `0x4c00` / `0x5000` | Ingress / egress bandwidth limit |
| `0x5800` | Broadcast bandwidth limit |
| `0x5c00` | Port mirroring |
| `0x6000` | Number of ports |
| `0x6800` | IGMP snooping |
| `0x9400` | Seen in the 2016 disclosure as a marker associated with *no authentication performed* on some firmware |

Port membership masks (`0x2400`, `0x2800`, mirror) are a single byte,
**MSB = port 1** (port 1 = `0x80` … port 8 = `0x01`); the GS105Ev2 uses only
the top 5 bits. This table was cross-checked against the `ProSafeLinux` and
`ngadmin` projects (see [`research.md`](research.md)) and reimplemented as
the `gs105e.nsdp` module — [`LIBRARY.md`](LIBRARY.md). None of the VLAN/write
codes are verified against this project's own hardware yet.

## Discovery query (what this project's client sends)

A read request: header as above with device MAC all-zero, opcode `0x01`,
body containing empty-value TLVs for model (`0x0001`), name (`0x0003`), MAC
(`0x0004`), IP (`0x0006`), DHCP (`0x000b`) and firmware (`0x000d`), followed
by the end marker. Devices on the local broadcast domain that still support
NSDP reply with opcode `0x02` and a body containing the corresponding value
TLVs. This is implemented in `NsdpClient.discover()` — see
[`LIBRARY.md`](LIBRARY.md).

## Known weaknesses (historical, see `research.md` for the full writeup)

- **Authentication bypass** (Westermann, 2016): on affected firmware
  (1.3.0.3, 1.4.0.2, and other GS/JGS/XS switches per NETGEAR's PSV-2015-0043
  advisory), write operations — including password change and firmware
  flash — could be issued without valid credentials.
- **Weak password obfuscation**: the admin password sent in NSDP write
  requests was "encrypted" with a repeating XOR against a fixed/known key,
  not real encryption.
- **Plaintext broadcast**: the (obfuscated) password was broadcast on the
  LAN by the configuration utility, observable to anyone on the same
  broadcast domain.

## Firmware update over NSDP

Historically, firmware update is a two-step process: an NSDP write enables a
TFTP server on the switch, then the new image is pushed over TFTP. This
project does not implement or exercise that path (see
[`../SECURITY.md`](../SECURITY.md) for scope).

## Current-firmware caveat

NETGEAR's own GS105Ev2 release notes state that **NSDP discovery was removed
starting firmware 1.6.0.15** in favor of UPnP-based discovery via the newer
NETGEAR Discovery Tool / Insight app. A switch already updated past 1.6.0.15
will not answer the query above even though it is reachable on the LAN by
other means (web UI, ARP). This has not yet been confirmed against this
project's own hardware.
