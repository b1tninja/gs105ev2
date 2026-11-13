# Firmware image — static analysis notes

First-pass static analysis of the two mirrored firmware images (see
[`../downloads/firmware/`](../downloads/firmware/)), using
[`../tools/fw_inspect.py`](../tools/fw_inspect.py) (a small stdlib-only
header/entropy/string scanner, written because the PyPI `binwalk` package
installed on this host turned out to be a non-functional stub — `import
binwalk` fails with `ModuleNotFoundError: No module named 'binwalk.core'` —
and a working binwalk build was not pursued for this first pass).

Analysis was done on the extracted `.bin` files copied into an isolated
scratch directory, per this workspace's rule for untrusted downloaded
files — not in-place inside `downloads/`.

## Chipset — confirmed

Both images contain the plaintext string **`RTL8367N`** (twice each, next to
a build-date string and a short version tag like `1.0.0`/`0.0`), and one
occurrence of **`RTL8367B`**. This confirms the switch silicon is a
**Realtek RTL8367N**, with the firmware apparently built to also recognize
an RTL8367B variant (sibling/alternate-SKU part). This resolves the open
chipset question from [`research.md`](research.md) without needing to open
the case.

```
V1.6.0.25:  0x000055f3  L,jRTL8367N
            0x00005602  L&$RTL8367N
V1.6.0.4:   0x000052de  L,jRTL8367N
            0x000052ed  L&$RTL8367N
            (RTL8367B found once in the same build-info region, offset not
             separately recorded this pass)
```

Build date strings next to this block: `Jun 09 2026` (V1.6.0.25 image —
NETGEAR's KB article date was 2026-07-02, consistent with a build shortly
before release) and `Feb 18 2019` (V1.6.0.4 image, matching that zip's
internal file timestamp exactly).

## Header

Neither image starts with a recognized standard container magic (no
U-Boot `uImage` header, no TRX `HDR0`, no SquashFS magic at offset 0). First
16 bytes:

```
V1.6.0.25: 21 43 65 87 00 0a 6b 68 00 00 05 c5 03 9d ad a2
V1.6.0.4:  21 43 65 87 00 0c 7a 2c 00 00 04 02 04 00 1e 35
```

`21 43 65 87` is a fixed 4-byte signature shared by both versions — almost
certainly a vendor-custom container/loader header (possibly nibble-reversed
or byte-swapped from a round value like `0x87654321`), **not yet decoded**.
Bytes 4-7 differ between the two versions and may encode a size, checksum,
or build ID — not determined this pass. This would be the next concrete
step if a full unpack is pursued: diff the header fields across more
versions once downloaded, and compare against the known-decoded Brother DJF
header work in the sibling `mfc9330cdw` project for methodology, since that
project also started from an undocumented vendor container.

## Software stack (from embedded strings)

- **Web UI server:** a small custom HTTP server, source path
  `..\..\common\src\app\web\httpd.c`, with its own strings
  (`HTTPD_MULTIPART_BOUNDARY_MAX`, `HTTPD_CLIENT_MAX`) — this is **not** a
  recognizable open-source httpd (Boa, mini_httpd, lighttpd); looks like
  part of a Realtek-supplied SDK ("common/src/app/..." tree), built on
  Windows (backslash paths embedded in the binary).
- **Network stack:** TCP state-machine strings (`LISTEN`, `SYN-SENT`,
  `ESTABLISHED`, `TIME-WAIT`, ...) plus source paths
  `..\..\common\src\lwps\icmp.c` and `..\..\common\src\lwps\tcp.c` point to
  an in-house or lwIP-derived stack referred to internally as `lwps`
  ("LightWeight Protocol Stack"?) rather than a stock upstream lwIP build —
  **not confirmed**, just the most likely reading of the path name.
- **Bootloader:** the web UI strings describe a separate "Bootloader
  Upgrade" flow expecting a file matching `GS105Ev2_loader_*`. That file
  was **not** present in either firmware zip downloaded from NETGEAR's
  support site — bootloader images for this model do not appear to be
  publicly distributed the same way the main firmware is.
- **Embedded assets:** numerous PNG images (web UI icons/graphics) embedded
  directly in the image, at the offsets `fw_inspect.py` reports.

No RTOS name (FreeRTOS, VxWorks, uC/OS, ...) was found in a plaintext-string
search; whatever runs under the SDK is either unnamed in strings or spelled
differently than the common names checked.

## Compression / entropy

The image is overwhelmingly "mid" or "low" entropy per 4 KiB block, with a
few "high" (>7.5 bits/byte) bands that correspond to runs of embedded PNGs
(already-compressed image data), not a separately compressed filesystem.
**No real gzip/SquashFS/JFFS2 containers were found** — the `JFFS2 magic`
and `gzip` hits `fw_inspect.py` reported are a **methodology lesson, not a
finding**: they are 2-byte magic sequences (`\x1f\x8b` for gzip,
`\x19\x85`/`\x85\x19` for JFFS2) that occur incidentally inside
already-compressed PNG data. Manually attempting `gzip.decompress()` at
every reported gzip offset in the 1.6.0.25 image failed for all of them
(`Unknown compression method` or "not a gzipped file") — confirming they
are false positives. A real unpack of this image would need the header
format decoded first (above), not a magic-byte scan.

## Conclusion for this pass

This is firmware for a small, flat, mostly-uncompressed embedded image: a
custom SDK (web server + "lwps" network stack) plus a Realtek RTL8367N
switch driver and embedded web-UI assets, wrapped in a vendor-custom header
that is not yet decoded. Going further (identifying the exact SoC's CPU core
and extracting executable code for disassembly) would need either the header
decoded or a real binwalk/Ghidra pass with signature-aware tooling, which is
out of scope for this first static-analysis pass.
