# `gs105e` Python library

An independent, stdlib-only NSDP client for NETGEAR GS105Ev2-class smart
switches. Protocol layout and TLV codes come from
[`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md) (cross-checked against the community
`ProSafeLinux`/`ngadmin` projects, cited in [`research.md`](research.md), then
reimplemented here); legal framing is in [`../LEGAL.md`](../LEGAL.md).

## Status / what's verified

- **Read paths** (`discover`, `get_info`, `get_version`, `get_port_speeds`,
  `get_vlans_8021q`, `get_pvids`) — implemented, and the wire-format
  encode/decode they rely on is **unit-tested** (`tests/test_nsdp.py`, 8
  deterministic tests, no hardware needed). The live round-trip against an
  actual switch is **not yet verified** — the device wasn't on the LAN when
  this was written (see [`PROBE-LOG.md`](PROBE-LOG.md)).
- **Write paths** (`set_name`, `set_dhcp`, `set_vlan_8021q`, `set_pvid`,
  and the `reboot`/`factory_reset` actions) — implemented but **gated and
  hardware-unverified**. They require `NsdpClient(allow_write=True,
  password=...)` and are **not exposed on the CLI**. See
  [`../SECURITY.md`](../SECURITY.md): writes are a separate, deliberate step,
  and NSDP write auth historically had serious weaknesses
  ([`WEBUI-AUTH.md`](WEBUI-AUTH.md), [`research.md`](research.md)).
- **Big caveat:** NETGEAR removed NSDP discovery from the switch side on
  firmware **1.6.0.15+**. On a current unit, every read here may legitimately
  return nothing even though the switch is alive — that's not a library bug.

## Install

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -e .
```

stdlib only — there are no runtime dependencies. The CLI entry point is
`gs105e`; `pytest` and `ruff` are the only dev tools.

## CLI (read-only)

```powershell
gs105e discover                               # broadcast, list every switch
gs105e --broadcast 192.168.1.255 discover     # subnet-directed broadcast
gs105e info    --ip 192.168.1.50              # full device info
gs105e version --ip 192.168.1.50
gs105e ports   --ip 192.168.1.50              # per-port link speed
gs105e vlans   --ip 192.168.1.50              # 802.1Q membership
gs105e pvids   --ip 192.168.1.50              # per-port default VLAN
```

With no running install, `python tools/nsdp_discover.py` runs discovery
directly off `src/` (zero-install wrapper).

## Library — reads

```python
from gs105e import NsdpClient

client = NsdpClient(timeout=3.0)

for sw in client.discover():
    print(sw.model, sw.mac, sw.ip, sw.firmware)

info = client.get_info(device_ip="192.168.1.50")
print(info.name, info.dhcp)

for ps in client.get_port_speeds(device_ip="192.168.1.50"):
    print(ps.port, ps.label)          # e.g. "1 1G/full"

for v in client.get_vlans_8021q(device_ip="192.168.1.50"):
    print(v.vlan_id, v.tagged_ports, v.untagged_ports)
```

## Library — VLAN writes (deliberate, unverified, your own switch only)

This is the home-network-segmentation use case the project exists for, but
it is **not tested against hardware** and can lock you out of the switch.
Enable writes explicitly and pass the admin password:

```python
from gs105e import NsdpClient, Vlan8021q

client = NsdpClient(allow_write=True, password="your-admin-password")
ip = "192.168.1.50"

# Put ports 1-2 on VLAN 10 untagged, port 5 tagged (uplink/trunk):
client.set_vlan_8021q(
    Vlan8021q(vlan_id=10, tagged_ports=[5], untagged_ports=[1, 2]),
    device_ip=ip,
)
# Make ports 1-2 default to VLAN 10 for untagged ingress:
client.set_pvid(1, 10, device_ip=ip)
client.set_pvid(2, 10, device_ip=ip)
```

A client built **without** `allow_write=True` raises `WriteNotAllowedError`
on any write, so the read-only default can't fire a write by accident.

Before trusting any of this against the real switch, confirm it is on
firmware that still speaks NSDP, verify each read round-trips, and change one
setting at a time with a way to recover (physical access / factory reset)
on hand.

## Port numbering

Ports are 1-based. VLAN/mirror membership is an 8-bit mask, MSB = port 1
(`ports_to_mask`/`mask_to_ports` in `gs105e.nsdp`); the GS105Ev2 uses only
the top 5 bits (`num_ports=5`, the client default).
