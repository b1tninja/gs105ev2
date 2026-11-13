"""Read-only NSDP discovery probe for NETGEAR GS105Ev2-class switches.

Broadcasts a single NSDP "read model" query on the local subnet and prints
any responding switch(es): IP, MAC, model, name, firmware version where the
reply includes them.

This is **read-only**: it never sends an NSDP write opcode. See
../SECURITY.md and ../LEGAL.md for scope. Protocol layout is documented in
../docs/NSDP-PROTOCOL.md.

Caveat: NETGEAR firmware 1.6.0.15+ removed NSDP discovery from the switch
side (see ../downloads/firmware/README.md); a switch on newer firmware may
not answer this query even though it is reachable by other means.
"""

from __future__ import annotations

import argparse
import socket
import struct
import time
from dataclasses import dataclass, field

NSDP_SIGNATURE = b"NSDP"
CLIENT_PORT = 63321
SWITCH_PORT = 63322
END_MARKER = b"\xff\xff\x00\x00"

OP_READ_REQUEST = 0x01
OP_READ_RESPONSE = 0x02

TLV_MODEL = 0x0001
TLV_NAME = 0x0003
TLV_MAC = 0x0004
TLV_LOCATION = 0x0005
TLV_IP = 0x0006
TLV_NETMASK = 0x0007
TLV_GATEWAY = 0x0008
TLV_FIRMWARE_1 = 0x000D
TLV_FIRMWARE_2 = 0x000E

TLV_NAMES = {
    TLV_MODEL: "model",
    TLV_NAME: "name",
    TLV_MAC: "mac",
    TLV_LOCATION: "location",
    TLV_IP: "ip",
    TLV_NETMASK: "netmask",
    TLV_GATEWAY: "gateway",
    TLV_FIRMWARE_1: "firmware_1",
    TLV_FIRMWARE_2: "firmware_2",
}


def _mac_str(raw: bytes) -> str:
    return ":".join(f"{b:02x}" for b in raw)


def _decode_value(tlv_type: int, value: bytes) -> str:
    if tlv_type == TLV_MAC:
        return _mac_str(value)
    if tlv_type in (TLV_IP, TLV_NETMASK, TLV_GATEWAY) and len(value) == 4:
        return ".".join(str(b) for b in value)
    try:
        return value.decode("utf-8").strip("\x00")
    except UnicodeDecodeError:
        return value.hex()


def build_discovery_request(host_mac: bytes, sequence: int) -> bytes:
    header = struct.pack(
        ">BBHI6s6sHH4s4s",
        0x01,  # protocol version
        OP_READ_REQUEST,
        0x0000,  # operation result
        0x00000000,  # unknown/reserved
        host_mac,
        b"\x00" * 6,  # device MAC: broadcast target
        0x0000,  # unknown/reserved
        sequence,
        NSDP_SIGNATURE,
        b"\x00" * 4,  # unknown/reserved
    )
    body = struct.pack(">HH", TLV_MODEL, 0)  # empty-value query for "model"
    return header + body + END_MARKER


def parse_response(packet: bytes) -> dict[str, str] | None:
    if len(packet) < 0x20 + 4 or packet[0x18:0x1C] != NSDP_SIGNATURE:
        return None
    opcode = packet[1]
    if opcode != OP_READ_RESPONSE:
        return None
    device_mac = packet[0x0E:0x14]
    fields: dict[str, str] = {"responder_mac": _mac_str(device_mac)}
    offset = 0x20
    while offset + 4 <= len(packet):
        tlv_type, length = struct.unpack(">HH", packet[offset : offset + 4])
        if tlv_type == 0xFFFF:
            break
        value = packet[offset + 4 : offset + 4 + length]
        name = TLV_NAMES.get(tlv_type, f"tlv_0x{tlv_type:04x}")
        fields[name] = _decode_value(tlv_type, value)
        offset += 4 + length
    return fields


@dataclass
class DiscoverOptions:
    timeout: float = 3.0
    broadcast: str = "255.255.255.255"
    host_mac: bytes = field(default_factory=lambda: b"\x00" * 6)


def discover(opts: DiscoverOptions) -> list[dict[str, str]]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(opts.timeout)
    try:
        sock.bind(("", CLIENT_PORT))
    except OSError:
        sock.bind(("", 0))

    request = build_discovery_request(opts.host_mac, sequence=int(time.time()) & 0xFFFF)
    sock.sendto(request, (opts.broadcast, SWITCH_PORT))

    responses: list[dict[str, str]] = []
    deadline = time.monotonic() + opts.timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sock.settimeout(remaining)
        try:
            packet, (addr, _port) = sock.recvfrom(4096)
        except socket.timeout:
            break
        fields = parse_response(packet)
        if fields is not None:
            fields["source_ip"] = addr
            responses.append(fields)
    sock.close()
    return responses


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout", type=float, default=3.0, help="seconds to wait for replies"
    )
    parser.add_argument(
        "--broadcast",
        default="255.255.255.255",
        help="broadcast address to send the query to (use a subnet-directed "
        "broadcast, e.g. 192.168.1.255, if the global broadcast is filtered)",
    )
    args = parser.parse_args()

    print(
        f"Sending NSDP discovery query to {args.broadcast}:{SWITCH_PORT} "
        f"(waiting up to {args.timeout}s for replies)..."
    )
    responses = discover(DiscoverOptions(timeout=args.timeout, broadcast=args.broadcast))

    if not responses:
        print(
            "No NSDP replies received. This means either: no switch on this "
            "subnet, the switch is on firmware 1.6.0.15+ (NSDP discovery "
            "removed, see docs/NSDP-PROTOCOL.md), or this host's network "
            "doesn't carry the broadcast to the switch's L2 segment."
        )
        return

    for i, fields in enumerate(responses, 1):
        print(f"\n--- Switch {i} ---")
        for key in ("source_ip", "responder_mac", "model", "name", "ip", "firmware_1", "firmware_2"):
            if key in fields:
                print(f"  {key}: {fields[key]}")
        extra = {k: v for k, v in fields.items() if k not in {
            "source_ip", "responder_mac", "model", "name", "ip", "firmware_1", "firmware_2",
        }}
        for key, value in extra.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
