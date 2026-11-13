"""High-level NSDP client: discovery, status reads, and (guarded) writes.

Read operations (``discover``, ``get_info``, ``get_port_speeds``,
``get_vlans_8021q``, ``get_pvids``) are safe and are the intended entry
point for this project's initial read-only scope (see ``../../SECURITY.md``).

Write operations (``set_name``, ``set_dhcp``, ``set_vlan_8021q``,
``set_pvid``, ``reboot``, ``factory_reset``) are implemented for
completeness but are **doubly gated**: the client must be constructed with
``allow_write=True`` and each write needs the admin ``password``. They are
**not verified against live hardware** and can lock out or disrupt the
switch — NSDP writes historically bypassed auth and used weak password
obfuscation (see ``docs/research.md`` and ``docs/WEBUI-AUTH.md``), and
NETGEAR removed NSDP discovery entirely on firmware 1.6.0.15+, so the write
path may not even be reachable on a current unit. Treat every write as an
explicit, deliberate, one-at-a-time action against a switch you own.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Sequence
from dataclasses import dataclass

from . import nsdp
from .nsdp import (
    Opcode,
    Packet,
    PortSpeed,
    Tlv,
    Vlan8021q,
    build_read_request,
    build_write_request,
)

DEFAULT_TIMEOUT = 3.0
GS105EV2_PORTS = 5


@dataclass(slots=True)
class SwitchInfo:
    """What a discovery/info read tells us about one switch."""

    source_ip: str
    mac: str | None = None
    model: str | None = None
    name: str | None = None
    ip: str | None = None
    netmask: str | None = None
    gateway: str | None = None
    dhcp: bool | None = None
    firmware: str | None = None


class NsdpError(RuntimeError):
    """An NSDP-level failure (non-zero status, or a refused write)."""


class WriteNotAllowedError(NsdpError):
    """A write was attempted on a client not constructed with allow_write."""


class NsdpClient:
    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        broadcast: str = "255.255.255.255",
        bind_host: str = "",
        host_mac: bytes = b"\x00" * 6,
        num_ports: int = GS105EV2_PORTS,
        allow_write: bool = False,
        password: str | None = None,
    ) -> None:
        self.timeout = timeout
        self.broadcast = broadcast
        self.bind_host = bind_host
        self.host_mac = host_mac
        self.num_ports = num_ports
        self.allow_write = allow_write
        self._password = password
        self._sequence = int(time.time()) & 0xFFFF

    # --- transport -------------------------------------------------------

    def _next_seq(self) -> int:
        self._sequence = (self._sequence + 1) & 0xFFFF
        return self._sequence

    def _socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((self.bind_host, nsdp.CLIENT_PORT))
        except OSError:
            sock.bind((self.bind_host, 0))
        sock.settimeout(self.timeout)
        return sock

    def _exchange(self, request: Packet, dest_ip: str) -> list[Packet]:
        """Send one request, collect replies until the timeout elapses."""
        sock = self._socket()
        try:
            sock.sendto(request.encode(), (dest_ip, nsdp.SWITCH_PORT))
            replies: list[Packet] = []
            deadline = time.monotonic() + self.timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                sock.settimeout(remaining)
                try:
                    data, (addr, _port) = sock.recvfrom(8192)
                except socket.timeout:
                    break
                try:
                    reply = Packet.decode(data)
                except ValueError:
                    continue
                if reply.opcode in (Opcode.READ_RESPONSE, Opcode.WRITE_RESPONSE):
                    reply_with_src = reply
                    replies.append(reply_with_src)
                    setattr(reply_with_src, "_source_ip", addr)
            return replies
        finally:
            sock.close()

    # --- reads -----------------------------------------------------------

    def discover(self) -> list[SwitchInfo]:
        """Broadcast a discovery query; return every switch that answers."""
        request = build_read_request(
            [Tlv.MODEL, Tlv.NAME, Tlv.MAC, Tlv.IP, Tlv.DHCP, Tlv.FIRMWARE_VER],
            host_mac=self.host_mac,
            sequence=self._next_seq(),
        )
        replies = self._exchange(request, self.broadcast)
        return [self._to_info(r) for r in replies]

    def query(
        self,
        tlv_types: Sequence[int],
        *,
        device_mac: bytes = b"\x00" * 6,
        device_ip: str | None = None,
    ) -> Packet:
        """Low-level: send a read request and return the first reply packet."""
        request = build_read_request(
            tlv_types,
            host_mac=self.host_mac,
            device_mac=device_mac,
            sequence=self._next_seq(),
        )
        replies = self._exchange(request, device_ip or self.broadcast)
        if not replies:
            raise NsdpError("no reply to read request")
        reply = replies[0]
        if reply.status != 0:
            raise NsdpError(f"switch returned status 0x{reply.status:04x}")
        return reply

    def get_info(
        self, *, device_mac: bytes = b"\x00" * 6, device_ip: str | None = None
    ) -> SwitchInfo:
        reply = self.query(
            [
                Tlv.MODEL,
                Tlv.NAME,
                Tlv.MAC,
                Tlv.IP,
                Tlv.NETMASK,
                Tlv.GATEWAY,
                Tlv.DHCP,
                Tlv.FIRMWARE_VER,
            ],
            device_mac=device_mac,
            device_ip=device_ip,
        )
        return self._to_info(reply)

    def get_version(
        self, *, device_mac: bytes = b"\x00" * 6, device_ip: str | None = None
    ) -> str | None:
        reply = self.query(
            [Tlv.FIRMWARE_VER], device_mac=device_mac, device_ip=device_ip
        )
        value = reply.first(Tlv.FIRMWARE_VER)
        return nsdp.decode_string(value) if value else None

    def get_port_speeds(
        self, *, device_mac: bytes = b"\x00" * 6, device_ip: str | None = None
    ) -> list[PortSpeed]:
        reply = self.query([Tlv.SPEED_STAT], device_mac=device_mac, device_ip=device_ip)
        return [PortSpeed.decode(v) for v in reply.all(Tlv.SPEED_STAT)]

    def get_vlans_8021q(
        self, *, device_mac: bytes = b"\x00" * 6, device_ip: str | None = None
    ) -> list[Vlan8021q]:
        reply = self.query([Tlv.VLAN_8021Q], device_mac=device_mac, device_ip=device_ip)
        return [Vlan8021q.decode(v, self.num_ports) for v in reply.all(Tlv.VLAN_8021Q)]

    def get_pvids(
        self, *, device_mac: bytes = b"\x00" * 6, device_ip: str | None = None
    ) -> dict[int, int]:
        reply = self.query([Tlv.VLAN_PVID], device_mac=device_mac, device_ip=device_ip)
        return dict(nsdp.decode_pvid(v) for v in reply.all(Tlv.VLAN_PVID))

    # --- writes (guarded, hardware-unverified) ---------------------------

    def _write(
        self,
        values: Sequence[tuple[int, bytes]],
        *,
        device_mac: bytes,
        device_ip: str | None,
    ) -> Packet:
        if not self.allow_write:
            raise WriteNotAllowedError(
                "writes are disabled; construct NsdpClient(allow_write=True) "
                "and pass an admin password. Writes are hardware-unverified — "
                "see the module docstring and SECURITY.md."
            )
        if self._password is None:
            raise WriteNotAllowedError("a write needs an admin password")
        # PASSWORD TLV first (order matters on some firmware), then the writes.
        payload: list[tuple[int, bytes]] = [
            (Tlv.PASSWORD, self._password.encode("utf-8"))
        ]
        payload.extend(values)
        request = build_write_request(
            payload,
            host_mac=self.host_mac,
            device_mac=device_mac,
            sequence=self._next_seq(),
        )
        replies = self._exchange(request, device_ip or self.broadcast)
        if not replies:
            raise NsdpError("no reply to write request")
        reply = replies[0]
        if reply.status != 0:
            raise NsdpError(f"write rejected, status 0x{reply.status:04x}")
        return reply

    def set_vlan_8021q(
        self,
        vlan: Vlan8021q,
        *,
        device_mac: bytes = b"\x00" * 6,
        device_ip: str | None = None,
    ) -> None:
        """Create/replace one 802.1Q VLAN membership row. UNVERIFIED."""
        self._write(
            [(Tlv.VLAN_8021Q, vlan.encode())],
            device_mac=device_mac,
            device_ip=device_ip,
        )

    def set_pvid(
        self,
        port: int,
        vlan_id: int,
        *,
        device_mac: bytes = b"\x00" * 6,
        device_ip: str | None = None,
    ) -> None:
        """Set a port's default (untagged) VLAN id. UNVERIFIED."""
        self._write(
            [(Tlv.VLAN_PVID, nsdp.encode_pvid(port, vlan_id))],
            device_mac=device_mac,
            device_ip=device_ip,
        )

    def set_name(
        self,
        name: str,
        *,
        device_mac: bytes = b"\x00" * 6,
        device_ip: str | None = None,
    ) -> None:
        """Set the switch's friendly name. UNVERIFIED."""
        self._write(
            [(Tlv.NAME, name.encode("utf-8"))],
            device_mac=device_mac,
            device_ip=device_ip,
        )

    def set_dhcp(
        self,
        enabled: bool,
        *,
        device_mac: bytes = b"\x00" * 6,
        device_ip: str | None = None,
    ) -> None:
        """Enable/disable DHCP. UNVERIFIED."""
        self._write(
            [(Tlv.DHCP, b"\x01" if enabled else b"\x00")],
            device_mac=device_mac,
            device_ip=device_ip,
        )

    # --- helpers ---------------------------------------------------------

    def _to_info(self, reply: Packet) -> SwitchInfo:
        def s(tlv: int) -> str | None:
            value = reply.first(tlv)
            return nsdp.decode_string(value) if value else None

        mac = reply.first(Tlv.MAC)
        ip = reply.first(Tlv.IP)
        netmask = reply.first(Tlv.NETMASK)
        gateway = reply.first(Tlv.GATEWAY)
        dhcp = reply.first(Tlv.DHCP)
        return SwitchInfo(
            source_ip=getattr(reply, "_source_ip", ""),
            mac=nsdp.decode_mac(mac) if mac else None,
            model=s(Tlv.MODEL),
            name=s(Tlv.NAME),
            ip=nsdp.decode_ipv4(ip) if ip and len(ip) == 4 else None,
            netmask=nsdp.decode_ipv4(netmask)
            if netmask and len(netmask) == 4
            else None,
            gateway=nsdp.decode_ipv4(gateway)
            if gateway and len(gateway) == 4
            else None,
            dhcp=(dhcp[-1] == 0x01) if dhcp else None,
            firmware=s(Tlv.FIRMWARE_VER),
        )


def discover(
    *, timeout: float = DEFAULT_TIMEOUT, broadcast: str = "255.255.255.255"
) -> list[SwitchInfo]:
    """Convenience one-shot discovery."""
    return NsdpClient(timeout=timeout, broadcast=broadcast).discover()
