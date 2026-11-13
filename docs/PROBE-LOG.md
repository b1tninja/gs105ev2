# Discovery probe runs

## 2026-11-13

Host: `192.0.2.70/24` (gateway `192.0.2.254`; `192.0.2.1` is a separate
lab bridge, not the gateway — see this host's own network notes).

```
python tools\nsdp_discover.py --timeout 4
python tools\nsdp_discover.py --timeout 4 --broadcast 192.0.2.255
```

Both runs: **no NSDP replies.** ARP table at the time showed
`192.0.2.1, .66, .67, .71 (known printer), .254` — no device
with a NETGEAR-pattern MAC and nothing new. Conclusion: **the GS105Ev2 is not
currently connected to this LAN segment** (or its power/uplink isn't plugged
in). This is the expected result, not a probe bug — rerun once the switch is
physically connected, and if it still doesn't answer, check whether it has
already been updated to firmware 1.6.0.15+ (NSDP discovery removed on-device,
see [`NSDP-PROTOCOL.md`](NSDP-PROTOCOL.md)) before assuming the probe itself
is wrong.
