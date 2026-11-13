# GS105Ev2 support downloads

Vendor firmware and utilities for the NETGEAR GS105Ev2, fetched directly from
NETGEAR's download CDN. This tree is **untracked** (see `../.gitignore`)
except for this file and the per-folder `README.md`/`HASHES.md` provenance
notes, same pattern as the sibling `mfc9330cdw`/`brother-firmware` projects.

## Layout

| Folder | Contents |
| --- | --- |
| `firmware/` | Official `.bin` firmware images + release notes, latest and one prior version |
| `utilities/` | NETGEAR Discovery Tool (NDT) for Windows |

## Re-run

```powershell
powershell -ExecutionPolicy Bypass -File ..\scripts\download-firmware.ps1
```

See [`firmware/README.md`](firmware/README.md) and
[`utilities/README.md`](utilities/README.md) for file-by-file provenance and
SHA-256 hashes.
