"""Independent NSDP client for NETGEAR GS105Ev2-class smart switches.

Read operations are safe and the intended entry point; writes are gated and
hardware-unverified (see ``client.py`` and ``../../SECURITY.md``). This is an
independent, unofficial project — see ``../../LEGAL.md``.
"""

from __future__ import annotations

from .client import (
    NsdpClient,
    NsdpError,
    SwitchInfo,
    WriteNotAllowedError,
    discover,
)
from .nsdp import (
    LinkSpeed,
    Opcode,
    Packet,
    PortSpeed,
    PortVlanBased,
    Tlv,
    Vlan8021q,
)

__version__ = "0.1.0"

__all__ = [
    "NsdpClient",
    "NsdpError",
    "WriteNotAllowedError",
    "SwitchInfo",
    "discover",
    "Packet",
    "Tlv",
    "Opcode",
    "Vlan8021q",
    "PortVlanBased",
    "PortSpeed",
    "LinkSpeed",
    "__version__",
]
