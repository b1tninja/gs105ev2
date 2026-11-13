# GS105Ev2 — switch deep-dive

Notes and tooling for a NETGEAR **GS105Ev2** ("5-Port Gigabit Ethernet Easy
Smart Switch" / ProSAFE Plus / Smart Managed Plus family): the NSDP
management protocol (UDP 63321-63324), the web UI, official firmware, and
prior public security research — groundwork for segmenting a home network
with VLANs using this switch, and general curiosity about what it runs.

Model confirmation: see [`docs/GS105Ev2.md`](docs/GS105Ev2.md). "Ev2" in the
name is the hardware/marketing revision; NETGEAR firmware for this model
currently tops out around `1.6.0.25` (see
[`downloads/firmware/README.md`](downloads/firmware/README.md)).

## Layout

| Path | Contents |
| --- | --- |
| [`docs/`](docs/) | Device identification, protocol notes, firmware format, research survey |
| [`tools/`](tools/) | Read-only NSDP discovery probe, firmware static-analysis helpers |
| [`scripts/`](scripts/) | Fetchers that rebuild `downloads/` from NETGEAR's site |
| `downloads/` ([notes](downloads/README.md)) | **Untracked** vendor firmware/utility artifacts + our provenance notes |

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

The discovery probe (`tools/nsdp_discover.py`) uses only the standard
library; the venv is only needed if later tooling adds dependencies.

```powershell
.\.venv\Scripts\python.exe tools\nsdp_discover.py
```

## Scope

Research targets a device owned by the author, for configuring/auditing it
ahead of a VLAN-segmented home network, interoperability, and security
analysis. This initial pass is **read-only discovery only** — no
configuration write, firmware flash, or exploitation of the vulnerabilities
in `docs/research.md` is attempted here.

This is an independent research effort by the device's owner. It is not
affiliated with, endorsed by, or sponsored by NETGEAR, Inc.; product names
and trademarks are the property of their respective owners.

## Security & rights

- Security issues in the device family discussed here can be reported
  privately — see [SECURITY.md](SECURITY.md).
- The notes, scripts, and documentation are the author's original work,
  provided under the MIT License — see [LICENSE](LICENSE).
- Legal framing for the reverse-engineering/interoperability work in this
  repository: [LEGAL.md](LEGAL.md), [DMCA.md](DMCA.md), [NOTICE](NOTICE).
