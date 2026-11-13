# VLAN isolation plan (GS105Ev2)

Design for using the GS105Ev2 to isolate a **work computer** from **personal
devices** on the home LAN. This is the switch-side plan; it has a hard
dependency on the network's L3 enforcement point, which is coordinated with
the infrastructure that owns `router` (see "Open dependencies" below).

**Status: planning only.** Nothing here has been applied — the switch is not
yet physically connected (no NSDP reply on the LAN as of 2026-11-13, see
[`PROBE-LOG.md`](PROBE-LOG.md)).

## The core constraint

A smart switch does **layer-2** VLAN separation. It is **not** a firewall and
cannot route or filter between VLANs. For "work cannot talk to personal, but
both reach the internet" you need an **L3 enforcement point** that:

- terminates both VLANs (802.1Q sub-interfaces),
- routes/NATs them out to the internet,
- and applies a firewall policy blocking work↔personal.

On this network (per the topology notes): `router` (192.0.2.1, Arch Linux,
inline bridge) is the only candidate — the ISP gateway at .254 does NAT but,
as consumer CPE, almost certainly can't do 802.1Q trunking or inter-VLAN
firewalling. So **the switch creates the VLANs; `router` enforces the
isolation.** That makes the risky, load-bearing part a `router` change, which
is the infra session's call.

## Recommended design (two VLANs + trunk)

With 5 ports: **1 trunk + 4 access**.

| Port | Role | VLAN membership | PVID |
| --- | --- | --- | --- |
| 1 | Trunk → `router` | tagged 10, tagged 20 (+ mgmt) | 1 (or mgmt) |
| 2 | Work computer | untagged 10 | 10 |
| 3 | Personal | untagged 20 | 20 |
| 4 | Personal | untagged 20 | 20 |
| 5 | Personal | untagged 20 | 20 |

- **VLAN 10 = work**, **VLAN 20 = personal.**
- The **trunk (port 1)** carries both VLANs tagged up to `router`, which runs
  `brLAN.10` / `brLAN.20` sub-interfaces, per-VLAN DHCP + DNS, and an nftables
  policy: allow each VLAN → internet (via .254), **drop 10↔20**.
- **Management plane stays on VLAN 10 (or a dedicated admin VLAN), never on a
  personal port, never internet-facing.** The GS105Ev2 management (web UI over
  plain HTTP, NSDP) is weak — see
  [`SECURITY-ANALYSIS.md`](SECURITY-ANALYSIS.md) /
  [`WEBUI-AUTH.md`](WEBUI-AUTH.md) — so it must sit where only trusted hosts
  can reach it. The switch's own management IP goes on the work/admin VLAN.

### Why 802.1Q and not port-based VLANs

The GS105Ev2 supports both. Port-based VLANs can't tag a trunk, so they can't
hand two separated VLANs to `router` over one uplink. 802.1Q with a tagged
trunk is required for the enforcement model above.

## Addressing

Isolation implies separate subnets so the L3 point can route/filter:

- VLAN 10 work: `192.0.10.0/24`, gateway `192.0.10.1` on `router`.
- VLAN 20 personal: `192.0.20.0/24`, gateway `192.0.20.1` on `router`.
- `router` does DHCP/DNS per VLAN and hairpin-NATs both out through .254.

(Alternative: keep flat `192.0.2.0/24` with private-VLAN-style isolation,
but that pushes all filtering onto `router` with ARP/proxy complexity and is
weaker — per-VLAN subnets are cleaner. Pending the infra session's call.)

## Applying it with the `gs105ev2` library

Once the switch is connected and its management IP is known, the switch side
is scriptable (and auditable) with this project's library — see
[`LIBRARY.md`](LIBRARY.md). Sketch (writes are hardware-unverified, gated, and
must be done deliberately with recovery on hand):

```python
from gs105ev2 import NsdpClient, Vlan8021q

sw = NsdpClient(allow_write=True, password="<admin>")
ip = "<switch mgmt ip>"

# VLAN 10 (work): port 2 untagged, trunk port 1 tagged
sw.set_vlan_8021q(Vlan8021q(10, tagged_ports=[1], untagged_ports=[2]), device_ip=ip)
# VLAN 20 (personal): ports 3-5 untagged, trunk port 1 tagged
sw.set_vlan_8021q(Vlan8021q(20, tagged_ports=[1], untagged_ports=[3, 4, 5]), device_ip=ip)
# PVIDs so untagged ingress lands on the right VLAN
sw.set_pvid(2, 10, device_ip=ip)
for p in (3, 4, 5):
    sw.set_pvid(p, 20, device_ip=ip)

# Audit read-back (safe):
for v in NsdpClient().get_vlans_8021q(device_ip=ip):
    print(v)
```

Read-only verification (`gs105ev2 vlans`, `gs105ev2 pvids`, `gs105ev2 ports`) should
confirm the config matches this table before trusting it.

## Open dependencies (coordinated with the infra session)

1. **Insertion point** — the switch must sit downstream of `router` so `router`
   is the trunk/enforcement point. If it hangs off the ISP gateway instead,
   this design doesn't hold.
2. **`router` as VLAN enforcer** — requires 802.1Q sub-interfaces + nftables on
   a box in the fiber path (house-offline risk; use the armed-revert method).
   Infra session's decision.
3. **Host → VLAN map** — which exact machines are work vs personal, and where
   shared boxes (file server, printer) go. If a shared box needs its own
   port, the 5-port budget breaks (→ bigger switch or a VLAN-aware AP).
4. **Addressing choice** — per-VLAN subnets vs. flat /24 private-VLAN.
5. **Firmware** — confirm the connected unit's firmware; on 1.6.0.15+ NSDP is
   gone and the switch is managed via the web UI, which changes how the
   library's write path (NSDP) can be used.

These are the questions sent to the infra session; this plan gets finalized to
a concrete port map once they're answered.
