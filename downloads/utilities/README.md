# GS105Ev2 official utilities

| Tool | Version | File | Source URL |
| --- | --- | --- | --- |
| NETGEAR Discovery Tool (NDT) for Windows | 2.0.4 | `NETGEAR_Discovery_Tool_Windows-V2.0.4.zip` | https://www.downloads.netgear.com/files/GDC/NDT/NETGEAR_Discovery_Tool_Windows-V2.0.4.zip |

NDT 2.0.4 supports both UPnP and NSDP discovery; Linux/macOS builds exist but
were not fetched here (Windows is the primary admin OS for this host). This
superseded the older, GS105E-family-specific "ProSAFE Plus Configuration
Utility" (PCU) / "Smart Control Center" naming once a switch is on firmware
1.6.0.15+ (NSDP broadcast discovery removed on-device; see
[`../firmware/README.md`](../firmware/README.md)). On older firmware, the
classic ProSAFE Plus Utility (>= V2.7.2 for firmware 1.6.0.3+) is still the
documented path — it was not re-downloaded here since NDT supersedes it for
current firmware.

## Hashes

See [`HASHES.md`](HASHES.md).
