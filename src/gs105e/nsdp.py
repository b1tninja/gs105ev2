"""NSDP (NETGEAR Switch Discovery Protocol) wire format.

Pure encode/decode of the protocol — no sockets here (see ``client.py`` for
I/O). The layout and TLV codes are documented in ``docs/NSDP-PROTOCOL.md``;
the TLV table and VLAN packing were cross-checked against the community
``ProSafeLinux`` and ``ngadmin`` projects (cited in ``docs/research.md``),
then independently reimplemented here.

Nothing in this module is verified against live GS105Ev2 hardware yet — the
device was not reachable when it was written. Read paths are deterministic
and unit-tested (``tests/test_nsdp.py``); the write opcodes and the few
write-only TLVs are implemented for completeness but carry a hardware-tested
caveat in ``client.py``.
"""

from __future__ import annotations

import struct
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import IntEnum

SIGNATURE = b"NSDP"
HEADER_LEN = 32
END_MARKER = b"\xff\xff\x00\x00"

# UDP ports. The client sends from CLIENT_PORT to SWITCH_PORT; replies come
# back to CLIENT_PORT. 63323/63324 are the documented interconnect variants.
CLIENT_PORT = 63321
SWITCH_PORT = 63322

PROTOCOL_VERSION = 0x01


class Opcode(IntEnum):
    READ_REQUEST = 0x01
    READ_RESPONSE = 0x02
    WRITE_REQUEST = 0x03
    WRITE_RESPONSE = 0x04


class Tlv(IntEnum):
    """Known NSDP TLV type codes.

    Incomplete and partly firmware-dependent — the upstream references flag
    their own tables as incomplete, and none of this is confirmed against
    this project's own hardware. See ``docs/NSDP-PROTOCOL.md``.
    """

    MODEL = 0x0001
    NAME = 0x0003
    MAC = 0x0004
    LOCATION = 0x0005
    IP = 0x0006
    NETMASK = 0x0007
    GATEWAY = 0x0008
    NEW_PASSWORD = 0x0009  # write-only
    PASSWORD = 0x000A  # write-only (auth on a write request)
    DHCP = 0x000B
    FIRMWARE_VER = 0x000D
    FIRMWARE_VER2 = 0x000E
    FIRMWARE_ACTIVE = 0x000F
    REBOOT = 0x0013  # write-only action
    FACTORY_RESET = 0x0400  # write-only action
    SPEED_STAT = 0x0C00
    PORT_STAT = 0x1000
    RESET_PORT_STAT = 0x1400  # write-only action
    VLAN_ENGINE = 0x2000  # which VLAN mode is enabled
    VLAN_PORT_BASED = 0x2400  # port-based VLAN membership
    VLAN_8021Q = 0x2800  # 802.1Q VLAN membership (tagged/untagged)
    VLAN_PVID = 0x3000  # per-port default VLAN id
    QOS = 0x3400
    PORT_BASED_QOS = 0x3800
    BANDWIDTH_IN = 0x4C00
    BANDWIDTH_OUT = 0x5000
    BROADCAST_BANDWIDTH = 0x5800
    PORT_MIRROR = 0x5C00
    NUMBER_OF_PORTS = 0x6000
    IGMP_SNOOPING = 0x6800
    BLOCK_UNKNOWN_MULTICAST = 0x6C00
    IGMP_HEADER_VALIDATION = 0x7000
    END = 0xFFFF


# TLV types that only make sense on a write request (never queried).
WRITE_ONLY_TLVS = frozenset(
    {
        Tlv.NEW_PASSWORD,
        Tlv.PASSWORD,
        Tlv.REBOOT,
        Tlv.FACTORY_RESET,
        Tlv.RESET_PORT_STAT,
    }
)


# --- port bitmask helpers -------------------------------------------------
#
# Port membership in VLAN/mirror TLVs is a single bitmask byte, MSB first:
# port 1 = 0x80, port 2 = 0x40, ... port 8 = 0x01. The GS105Ev2 has 5 ports,
# so only the top 5 bits are meaningful on this model, but the helpers stay
# general (up to 8 ports).

MAX_PORTS = 8


def ports_to_mask(ports: Iterable[int]) -> int:
    """Pack a set of 1-based port numbers into an NSDP bitmask byte."""
    mask = 0
    for port in ports:
        if not 1 <= port <= MAX_PORTS:
            raise ValueError(f"port {port} out of range 1..{MAX_PORTS}")
        mask |= 1 << (MAX_PORTS - port)
    return mask


def mask_to_ports(mask: int, num_ports: int = MAX_PORTS) -> list[int]:
    """Unpack an NSDP bitmask byte into sorted 1-based port numbers."""
    return [
        port for port in range(1, num_ports + 1) if mask & (1 << (MAX_PORTS - port))
    ]


# --- value codecs ---------------------------------------------------------


def decode_mac(value: bytes) -> str:
    return ":".join(f"{b:02x}" for b in value)


def encode_mac(mac: str) -> bytes:
    raw = bytes.fromhex(mac.replace(":", "").replace("-", ""))
    if len(raw) != 6:
        raise ValueError(f"not a 6-byte MAC: {mac!r}")
    return raw


def decode_ipv4(value: bytes) -> str:
    if len(value) != 4:
        raise ValueError(f"not a 4-byte IPv4: {value!r}")
    return ".".join(str(b) for b in value)


def encode_ipv4(addr: str) -> bytes:
    parts = [int(p) for p in addr.split(".")]
    if len(parts) != 4 or any(not 0 <= p <= 255 for p in parts):
        raise ValueError(f"not an IPv4 address: {addr!r}")
    return bytes(parts)


def decode_string(value: bytes) -> str:
    return value.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


# --- packet ---------------------------------------------------------------


@dataclass(slots=True)
class Packet:
    """One NSDP datagram: a 32-byte header plus a list of (type, value) TLVs.

    ``tlvs`` preserves order and allows duplicate types (the switch returns a
    separate TLV per port/VLAN for the table-valued codes).
    """

    opcode: Opcode
    host_mac: bytes = b"\x00" * 6
    device_mac: bytes = b"\x00" * 6
    sequence: int = 0
    tlvs: list[tuple[int, bytes]] = field(default_factory=list)
    version: int = PROTOCOL_VERSION
    status: int = 0

    def encode(self) -> bytes:
        if len(self.host_mac) != 6 or len(self.device_mac) != 6:
            raise ValueError("host_mac and device_mac must each be 6 bytes")
        header = struct.pack(
            ">BBH4x6s6s2xH4s4x",
            self.version,
            int(self.opcode),
            self.status,
            self.host_mac,
            self.device_mac,
            self.sequence & 0xFFFF,
            SIGNATURE,
        )
        body = bytearray()
        for tlv_type, value in self.tlvs:
            body += struct.pack(">HH", int(tlv_type), len(value))
            body += value
        return bytes(header) + bytes(body) + END_MARKER

    @classmethod
    def decode(cls, data: bytes) -> Packet:
        if len(data) < HEADER_LEN:
            raise ValueError(f"packet shorter than {HEADER_LEN}-byte header")
        if data[24:28] != SIGNATURE:
            raise ValueError("missing NSDP signature at offset 24")
        version, opcode, status = struct.unpack(">BBH", data[0:4])
        host_mac = data[8:14]
        device_mac = data[14:20]
        sequence = struct.unpack(">H", data[22:24])[0]

        tlvs: list[tuple[int, bytes]] = []
        pos = HEADER_LEN
        while pos + 4 <= len(data):
            tlv_type, length = struct.unpack(">HH", data[pos : pos + 4])
            if tlv_type == Tlv.END:
                break
            pos += 4
            value = data[pos : pos + length]
            if len(value) != length:
                raise ValueError(
                    f"truncated TLV 0x{tlv_type:04x}: "
                    f"want {length} bytes, have {len(value)}"
                )
            tlvs.append((tlv_type, value))
            pos += length

        return cls(
            opcode=Opcode(opcode),
            host_mac=host_mac,
            device_mac=device_mac,
            sequence=sequence,
            tlvs=tlvs,
            version=version,
            status=status,
        )

    def first(self, tlv_type: int) -> bytes | None:
        """Value of the first TLV of ``tlv_type``, or None if absent."""
        for t, value in self.tlvs:
            if t == tlv_type:
                return value
        return None

    def all(self, tlv_type: int) -> list[bytes]:
        """Values of every TLV of ``tlv_type`` (for table-valued codes)."""
        return [value for t, value in self.tlvs if t == tlv_type]


def build_read_request(
    tlv_types: Sequence[int],
    *,
    host_mac: bytes = b"\x00" * 6,
    device_mac: bytes = b"\x00" * 6,
    sequence: int = 0,
) -> Packet:
    """A read request asking for each of ``tlv_types`` (empty-value TLVs)."""
    return Packet(
        opcode=Opcode.READ_REQUEST,
        host_mac=host_mac,
        device_mac=device_mac,
        sequence=sequence,
        tlvs=[(int(t), b"") for t in tlv_types],
    )


def build_write_request(
    values: Sequence[tuple[int, bytes]],
    *,
    host_mac: bytes = b"\x00" * 6,
    device_mac: bytes = b"\x00" * 6,
    sequence: int = 0,
) -> Packet:
    """A write request carrying ``(tlv_type, encoded_value)`` pairs.

    The caller is responsible for ordering (the authentication PASSWORD TLV,
    where used, is order-sensitive on some firmware).
    """
    return Packet(
        opcode=Opcode.WRITE_REQUEST,
        host_mac=host_mac,
        device_mac=device_mac,
        sequence=sequence,
        tlvs=[(int(t), v) for t, v in values],
    )


# --- 802.1Q VLAN value codec ----------------------------------------------


@dataclass(slots=True)
class Vlan8021q:
    """One 802.1Q VLAN membership row (TLV 0x2800)."""

    vlan_id: int
    tagged_ports: list[int]
    untagged_ports: list[int]

    def encode(self) -> bytes:
        return struct.pack(
            ">HBB",
            self.vlan_id,
            ports_to_mask(self.tagged_ports),
            ports_to_mask(self.untagged_ports),
        )

    @classmethod
    def decode(cls, value: bytes, num_ports: int = MAX_PORTS) -> Vlan8021q:
        vlan_id, tagged, untagged = struct.unpack(">HBB", value[:4])
        return cls(
            vlan_id=vlan_id,
            tagged_ports=mask_to_ports(tagged, num_ports),
            untagged_ports=mask_to_ports(untagged, num_ports),
        )


@dataclass(slots=True)
class PortVlanBased:
    """One port-based VLAN membership row (TLV 0x2400)."""

    vlan_id: int
    ports: list[int]

    def encode(self) -> bytes:
        return struct.pack(">HB", self.vlan_id, ports_to_mask(self.ports))

    @classmethod
    def decode(cls, value: bytes, num_ports: int = MAX_PORTS) -> PortVlanBased:
        vlan_id, mask = struct.unpack(">HB", value[:3])
        return cls(vlan_id=vlan_id, ports=mask_to_ports(mask, num_ports))


def encode_pvid(port: int, vlan_id: int) -> bytes:
    """Encode a per-port PVID value (TLV 0x3000)."""
    if not 1 <= port <= MAX_PORTS:
        raise ValueError(f"port {port} out of range")
    return struct.pack(">BH", port, vlan_id)


def decode_pvid(value: bytes) -> tuple[int, int]:
    """Decode a per-port PVID value into ``(port, vlan_id)``."""
    port, vlan_id = struct.unpack(">BH", value[:3])
    return port, vlan_id


class LinkSpeed(IntEnum):
    NONE = 0x00
    TEN_HALF = 0x01
    TEN_FULL = 0x02
    HUNDRED_HALF = 0x03
    HUNDRED_FULL = 0x04
    GIGABIT = 0x05


SPEED_LABELS: Mapping[int, str] = {
    LinkSpeed.NONE: "down",
    LinkSpeed.TEN_HALF: "10M/half",
    LinkSpeed.TEN_FULL: "10M/full",
    LinkSpeed.HUNDRED_HALF: "100M/half",
    LinkSpeed.HUNDRED_FULL: "100M/full",
    LinkSpeed.GIGABIT: "1G/full",
}


@dataclass(slots=True)
class PortSpeed:
    """One port speed/link row (TLV 0x0c00)."""

    port: int
    speed: int

    @property
    def label(self) -> str:
        return SPEED_LABELS.get(self.speed, f"0x{self.speed:02x}")

    @classmethod
    def decode(cls, value: bytes) -> PortSpeed:
        port, speed = struct.unpack(">BB", value[:2])
        return cls(port=port, speed=speed)
