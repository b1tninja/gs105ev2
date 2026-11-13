# Firmware image — static analysis notes

Static analysis of the GS105Ev2 firmware images (see
[`../downloads/firmware/`](../downloads/firmware/)), using a small stdlib
scanner ([`../tools/fw_inspect.py`](../tools/fw_inspect.py)) plus **real
binwalk 3.1.0** (installed via `cargo install binwalk`, since the PyPI
`binwalk` package on this host is a non-functional legacy stub — `import
binwalk` fails with `ModuleNotFoundError: No module named 'binwalk.core'`;
ReFirmLabs' maintained binwalk is now a Rust rewrite, not a PyPI package).
Also pulled **8 total firmware versions** from NETGEAR's download CDN
(`1.6.0.4`, `.6`, `.10`, `.11`, `.15`, `.21`, `.24`, `.25`) purely to diff
across versions and separate "fixed container structure" from
"version-specific payload" — only `.4` and `.25` are kept in this repo's
`downloads/firmware/` (see that folder's `README.md`); the rest were
fetched to an isolated scratch directory for this analysis and not
preserved.

Analysis was done on extracted `.bin` files copied into an isolated scratch
directory, per this workspace's rule for untrusted downloaded files — not
in-place inside `downloads/`.

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

## Header — decoded (20 bytes), from an 8-version corpus

Diffing all 8 downloaded versions pinned down a **fixed 20-byte header**,
not just a magic number:

| Offset | Size | Field | Value |
| --- | --- | --- | --- |
| `0x00` | 4 | Magic | `0x87654321`, little-endian (`21 43 65 87` on disk) — **identical in all 8 versions** |
| `0x04` | 4 | Payload length, big-endian | exactly `file_size - 20` in **all 8 versions** |
| `0x08` | 4 | Unidentified; high 16 bits always `0x0000` in all 8 samples | low 16 bits range `0x0402`-`0x05c5` (1026-1477) across the 8 versions, loosely but not monotonically increasing with build recency |
| `0x0C` | 4 | Unidentified, full 32-bit range used | top byte is `0x03` or `0x04` in all 8 samples — too clustered to be a general CRC32 of the variable-length payload (those are uniformly distributed); more likely a checksum over a small/fixed-size region, a load address, or a version-encoded field |
| `0x10` | 4 | Fixed sub-header marker | `0x332255ff` (big-endian) — **identical in all 8 versions** |
| `0x14` | — | Payload starts here | |

Confirmed with a small script comparing `struct.unpack(">I", header[4:8])[0]`
against `len(data) - 20` for all 8 files — matched exactly every time. The
two unidentified 4-byte fields (offsets `0x08` and `0x0C`) were tested
against `zlib.crc32()` of the payload and did **not** match in any sample;
pinning them down further would need either more samples correlated against
known build metadata, or disassembling the bootloader/loader code that
presumably validates this header (not attempted this pass — no bootloader
image was obtainable, see below).

This is a vendor-custom container, not a standard one: no U-Boot `uImage`
header, no TRX `HDR0`, no SquashFS magic at offset 0 in any sample.

## Payload prefix — likely CPU boot stub, and a chip-core hypothesis

The first **13 bytes immediately after the 20-byte header** (`02 10 16 02
10 09 8f 96 22 32 00 02 2e`) are **byte-for-byte identical across all 8
firmware versions**. A few version-specific bytes follow (plausibly an
address/size immediate operand that shifts with code size), then another
long run of **identical bytes across all 8 versions** (`78 7f e4 f6 d8 fd
75 ...`). This pattern — short constant runs interrupted by small
build-specific fields — is exactly what a fixed CPU reset/boot vector looks
like when it contains an absolute jump/load-immediate to the (slightly
shifting) application entry point.

**Working hypothesis, not yet confirmed with a disassembler:** the high
density of the byte `0x75` in this region (visible throughout the header
dump above and the constant runs) matches the **Intel 8051** opcode `0x75`
(`MOV direct,#data`) — a very common instruction in 8051 startup code that
initializes SFRs/variables with immediate values. Combined with the
Windows-style backslash build paths and the unfamiliar "lwps"/custom-httpd
SDK (below), an **8051-family microcontroller core** (common in
Realtek's own switch-management SDKs for this chip generation) is a
plausible fit — more plausible than MIPS, which was the default assumption
for "Realtek switch SoC" going in. This needs a real disassembler (Ghidra,
with its 8051 processor module) pointed at the payload to confirm; it is
not established fact yet.

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

## Compression / entropy — corrected with real binwalk

**Correction from an earlier pass of this document:** a first-pass scan with
the hand-written `fw_inspect.py` tool, before a working binwalk was
available, found 2-byte `\x1f\x8b` ("gzip") matches that manual
`gzip.decompress()` calls failed to open, and concluded they were false
positives from compressed PNG data. **That conclusion was wrong for most of
them.** Running real **binwalk 3.1.0** against `GS105Ev2_V1.6.0.25.bin`
found 11 genuine, individually-gzipped web UI assets, each with a valid
gzip header carrying the **original filename and a Unix build timestamp**:

```
de.js, en.js, ja.js          — localized UI strings (German/English/Japanese)
frame.js, function.js        — UI logic
help.js, help.css            — help pane
login.js, login.css          — login page (see docs/WEBUI-AUTH.md)
jquery.md5.js                — client-side MD5 (used by the login scheme)
style.css                    — main stylesheet
```

All 11 carry the identical embedded timestamp `2026-06-09 01:03:34 UTC`,
matching the `Jun 09 2026` build-date string found earlier right next to
the `RTL8367N` version block — strong corroboration that the whole image is
one coherent build. Manually decompressing all 11 at binwalk's reported
offsets (`gzip.GzipFile(...).read()`) succeeded for every one, confirming
binwalk's offsets are exact (the earlier manual test had simply used wrong
offsets, copied from the pre-binwalk magic-byte scan rather than from a
validated gzip-stream parse).

**Lesson, now correctly stated:** a 2-byte magic-byte scan without
structural validation (`fw_inspect.py`'s approach) cannot reliably
distinguish a real gzip stream from an incidental 2-byte match inside other
compressed data (several of the `fw_inspect.py` "gzip" hits genuinely were
coincidental matches inside the embedded PNGs) — but it also isn't reliable
enough to rule hits *out* without checking each one properly, which is what
went wrong the first time. Real binwalk (or any tool that parses the full
gzip header, including its length/CRC trailer) is the right tool for this,
not a hand-rolled scanner — use `fw_inspect.py` only for the
entropy/printable-string pass binwalk doesn't do by default.

The image is otherwise "mid"/"low" entropy per 4 KiB block outside these
gzip blocks and the embedded PNGs (already-compressed image data) —
consistent with a flat, mostly-uncompressed executable image plus a handful
of individually-compressed text/web assets, not a compressed filesystem
(SquashFS/JFFS2) — binwalk found no SquashFS/JFFS2 container signature
matches in either image.

## Extracted web assets are not redistributed here

The 11 decompressed JS/CSS files were extracted into the same isolated
scratch directory as the firmware itself (not this repository) to read
`login.js` for [`WEBUI-AUTH.md`](WEBUI-AUTH.md); per [`../LEGAL.md`](../LEGAL.md)
this repository does not redistribute vendor-copyrighted web assets, so
they are not committed or mirrored anywhere here.

## Conclusion for this pass

This is firmware for a small, mostly-uncompressed embedded image: a custom
SDK (web server + "lwps" network stack, likely **8051-family** code per the
boot-stub hypothesis above — not yet confirmed) plus a Realtek RTL8367N
switch driver, embedded PNGs, and 11 gzip-compressed localized web-UI
assets, wrapped in a now mostly-decoded 20-byte vendor header (magic,
payload length, two still-unidentified fields, a fixed sub-header marker).
Confirming the CPU core and extracting executable code for real
disassembly is the natural next step, and is what `ghidra-mcp` is for —
not attempted in this pass.
