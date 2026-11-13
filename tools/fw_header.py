"""Parse the GS105Ev2 firmware container's 20-byte header.

Layout decoded in ../docs/FIRMWARE-FORMAT.md from an 8-version corpus diff:

    0x00  4   magic, little-endian 0x87654321 (constant across all versions)
    0x04  4   payload length, big-endian, == file_size - 20 (constant formula)
    0x08  4   unidentified (high 16 bits always 0 in the samples checked)
    0x0C  4   unidentified (not a zlib.crc32 of the payload)
    0x10  4   fixed sub-header marker, big-endian 0x332255ff (constant)
    0x14  -   payload starts here

Usage: python tools/fw_header.py <path-to-bin> [...]
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

HEADER_LEN = 20
EXPECTED_MAGIC = 0x87654321
EXPECTED_MARKER = 0x332255FF


def parse_header(data: bytes) -> dict[str, int | bool]:
    if len(data) < HEADER_LEN:
        raise ValueError("file shorter than the 20-byte header")
    magic = struct.unpack_from("<I", data, 0x00)[0]
    length = struct.unpack_from(">I", data, 0x04)[0]
    field8 = struct.unpack_from(">I", data, 0x08)[0]
    field12 = struct.unpack_from(">I", data, 0x0C)[0]
    marker = struct.unpack_from(">I", data, 0x10)[0]
    return {
        "magic": magic,
        "magic_ok": magic == EXPECTED_MAGIC,
        "declared_payload_length": length,
        "actual_payload_length": len(data) - HEADER_LEN,
        "length_ok": length == len(data) - HEADER_LEN,
        "field_0x08": field8,
        "field_0x0C": field12,
        "marker": marker,
        "marker_ok": marker == EXPECTED_MARKER,
    }


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    for arg in argv:
        data = Path(arg).read_bytes()
        info = parse_header(data)
        print(f"{arg}:")
        for key, value in info.items():
            if isinstance(value, bool):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value} (0x{value:x})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
