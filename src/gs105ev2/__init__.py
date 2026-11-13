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
    Bandwidth,
    BandwidthLimit,
    LinkSpeed,
    Opcode,
    Packet,
    PortMirror,
    PortSpeed,
    PortStat,
    PortVlanBased,
    QosMode,
    Tlv,
    Vlan8021q,
    VlanEngineMode,
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
    "PortStat",
    "LinkSpeed",
    "VlanEngineMode",
    "QosMode",
    "Bandwidth",
    "BandwidthLimit",
    "PortMirror",
    "__version__",
]
