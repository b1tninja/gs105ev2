"""Deterministic unit tests for the NSDP wire format.

These need no hardware — they exercise encode/decode, the port bitmask, and
the VLAN/PVID/speed codecs against hand-computed byte vectors. The live read
and write paths in client.py can only be verified against an actual switch
(not present when this was written); see docs/GHIDRA-NOTES.md / SECURITY.md.
"""

from __future__ import annotations

import struct

from gs105e import nsdp
from gs105e.nsdp import (
    Opcode,
    Packet,
    PortSpeed,
    Tlv,
    Vlan8021q,
    build_read_request,
)


def test_header_is_32_bytes_with_signature() -> None:
    pkt = Packet(opcode=Opcode.READ_REQUEST)
    raw = pkt.encode()
    assert raw[0] == nsdp.PROTOCOL_VERSION
    assert raw[1] == Opcode.READ_REQUEST
    assert raw[24:28] == b"NSDP"
    # empty body => header + end marker only
    assert len(raw) == nsdp.HEADER_LEN + len(nsdp.END_MARKER)
    assert raw.endswith(nsdp.END_MARKER)


def test_read_request_round_trip() -> None:
    host = bytes.fromhex("001122334455")
    req = build_read_request(
        [Tlv.MODEL, Tlv.MAC, Tlv.FIRMWARE_VER], host_mac=host, sequence=0x1234
    )
    raw = req.encode()
    back = Packet.decode(raw)
    assert back.opcode == Opcode.READ_REQUEST
    assert back.host_mac == host
    assert back.sequence == 0x1234
    assert [t for t, _ in back.tlvs] == [Tlv.MODEL, Tlv.MAC, Tlv.FIRMWARE_VER]
    assert all(v == b"" for _, v in back.tlvs)


def test_decode_parses_tlv_values_and_stops_at_end() -> None:
    body = (
        struct.pack(">HH", Tlv.MODEL, 8)
        + b"GS105Ev2"
        + struct.pack(">HH", Tlv.MAC, 6)
        + bytes.fromhex("3c2af435905f")
    )
    header = Packet(opcode=Opcode.READ_RESPONSE).encode()[:32]
    raw = header + body + nsdp.END_MARKER + b"garbage-after-end"
    pkt = Packet.decode(raw)
    assert pkt.opcode == Opcode.READ_RESPONSE
    assert nsdp.decode_string(pkt.first(Tlv.MODEL)) == "GS105Ev2"
    assert nsdp.decode_mac(pkt.first(Tlv.MAC)) == "3c:2a:f4:35:90:5f"


def test_port_bitmask_msb_first() -> None:
    # port 1 is the high bit, port 8 the low bit
    assert nsdp.ports_to_mask([1]) == 0x80
    assert nsdp.ports_to_mask([8]) == 0x01
    assert nsdp.ports_to_mask([1, 2, 3, 4, 5]) == 0xF8
    assert nsdp.mask_to_ports(0xF8, num_ports=5) == [1, 2, 3, 4, 5]
    # a 5-port switch ignores bits for ports 6-8
    assert nsdp.mask_to_ports(0xFF, num_ports=5) == [1, 2, 3, 4, 5]


def test_vlan_8021q_round_trip() -> None:
    vlan = Vlan8021q(vlan_id=10, tagged_ports=[5], untagged_ports=[1, 2])
    raw = vlan.encode()
    assert raw == struct.pack(">HBB", 10, 0x08, 0xC0)
    back = Vlan8021q.decode(raw, num_ports=5)
    assert back.vlan_id == 10
    assert back.tagged_ports == [5]
    assert back.untagged_ports == [1, 2]


def test_pvid_round_trip() -> None:
    raw = nsdp.encode_pvid(port=3, vlan_id=20)
    assert raw == struct.pack(">BH", 3, 20)
    assert nsdp.decode_pvid(raw) == (3, 20)


def test_port_speed_decode() -> None:
    gig = PortSpeed.decode(struct.pack(">BB", 1, 0x05))
    assert gig.port == 1
    assert gig.label == "1G/full"
    down = PortSpeed.decode(struct.pack(">BB", 2, 0x00))
    assert down.label == "down"


def test_decode_rejects_short_and_unsigned() -> None:
    try:
        Packet.decode(b"too short")
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on short packet")

    bad_sig = bytearray(Packet(opcode=Opcode.READ_REQUEST).encode())
    bad_sig[24:28] = b"XXXX"
    try:
        Packet.decode(bytes(bad_sig))
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError on bad signature")
