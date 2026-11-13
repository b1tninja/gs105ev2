"""Static, read-only inspection of a GS105Ev2 firmware .bin image.

No binwalk dependency (the PyPI `binwalk` package is a non-functional stub on
this host; a real binwalk build was not pursued for this first pass). Prints:
header/footer hex, printable-string runs, a coarse Shannon-entropy profile
(to spot compressed/encrypted regions), and any known container magic bytes.

Usage: python tools/fw_inspect.py <path-to-bin> [...]

Pass the firmware path as an argument; do not run this from inside the
downloads/ directory with the firmware as the working directory (see
AGENTS.md on untrusted downloaded files).
"""

from __future__ import annotations

import math
import re
import sys
from pathlib import Path

CHUNK = 4096
PRINTABLE = re.compile(rb"[\x20-\x7e]{6,}")

KNOWN_MAGICS: list[tuple[bytes, str]] = [
    (b"hsqs", "SquashFS (little-endian)"),
    (b"sqsh", "SquashFS (big-endian)"),
    (b"\x1f\x8b", "gzip"),
    (b"\x5d\x00\x00", "raw LZMA (common first bytes)"),
    (b"\x89PNG", "PNG"),
    (b"uImag", "U-Boot uImage ('uImage' partial)"),
    (b"\x27\x05\x19\x56", "U-Boot uImage header magic"),
    (b"CrcH", "TRX firmware header (partial)"),
    (b"HDR0", "TRX firmware header"),
    (b"JFFS2", "JFFS2 (string match, not magic)"),
    (b"\x85\x19", "JFFS2 magic (BE)"),
    (b"\x19\x85", "JFFS2 magic (LE)"),
    (b"7zXZ", "XZ container"),
    (b"BZh", "bzip2"),
    (b"PK\x03\x04", "ZIP"),
]


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    n = len(data)
    entropy = 0.0
    for c in counts:
        if c:
            p = c / n
            entropy -= p * math.log2(p)
    return entropy


def entropy_profile(data: bytes, chunk: int = CHUNK) -> list[tuple[int, float]]:
    return [
        (offset, shannon_entropy(data[offset : offset + chunk]))
        for offset in range(0, len(data), chunk)
    ]


def find_magics(data: bytes) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    for magic, label in KNOWN_MAGICS:
        start = 0
        while True:
            idx = data.find(magic, start)
            if idx == -1:
                break
            hits.append((idx, label))
            start = idx + 1
    hits.sort()
    return hits


def printable_runs(data: bytes, limit: int = 40) -> list[tuple[int, bytes]]:
    runs = []
    for m in PRINTABLE.finditer(data):
        runs.append((m.start(), m.group()))
        if len(runs) >= limit:
            break
    return runs


def inspect(path: Path) -> None:
    data = path.read_bytes()
    print(f"=== {path.name} ({len(data)} bytes) ===")
    print(f"Header (first 64 bytes): {data[:64].hex()}")
    print(f"Footer (last 64 bytes):  {data[-64:].hex()}")

    print("\n-- Known magic bytes found --")
    hits = find_magics(data)
    if not hits:
        print("  (none of the known magics in KNOWN_MAGICS matched)")
    for offset, label in hits[:30]:
        print(f"  0x{offset:08x}  {label}")
    if len(hits) > 30:
        print(f"  ... and {len(hits) - 30} more")

    print("\n-- Entropy profile (4KiB blocks; >7.5 suggests compressed/encrypted) --")
    profile = entropy_profile(data)
    # Summarize as runs of similar entropy to keep output short.
    bands = []
    for offset, ent in profile:
        band = "high" if ent > 7.5 else ("mid" if ent > 5.0 else "low")
        if bands and bands[-1][1] == band:
            bands[-1] = (bands[-1][0], band, offset + CHUNK)
        else:
            bands.append((offset, band, offset + CHUNK))
    for start, band, end in bands:
        print(f"  0x{start:08x}-0x{end:08x}  {band}")

    print("\n-- First printable ASCII runs (>=6 chars) --")
    for offset, run in printable_runs(data):
        print(f"  0x{offset:08x}  {run[:80]!r}")


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    for arg in argv:
        inspect(Path(arg))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
