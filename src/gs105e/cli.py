"""Command-line entry point: ``gs105e <subcommand>``.

Read-only subcommands (``discover``, ``info``, ``version``, ``ports``,
``vlans``, ``pvids``) only. Writes are deliberately not exposed on the CLI —
they are hardware-unverified and risky (see ``client.py``); drive them from
Python with an explicit ``NsdpClient(allow_write=True, password=...)`` if you
really mean to.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from .client import DEFAULT_TIMEOUT, NsdpClient, NsdpError, SwitchInfo


def _print_info(info: SwitchInfo) -> None:
    fields = [
        ("source_ip", info.source_ip),
        ("model", info.model),
        ("name", info.name),
        ("mac", info.mac),
        ("ip", info.ip),
        ("netmask", info.netmask),
        ("gateway", info.gateway),
        ("dhcp", info.dhcp),
        ("firmware", info.firmware),
    ]
    for key, value in fields:
        if value is not None and value != "":
            print(f"  {key}: {value}")


def _no_reply_hint() -> None:
    print(
        "No switch answered. Either none is on this subnet, the switch is on "
        "firmware 1.6.0.15+ (NSDP discovery removed on-device - see "
        "docs/NSDP-PROTOCOL.md), or the broadcast doesn't reach its L2 "
        "segment. Try --broadcast <subnet-broadcast>, e.g. 192.168.1.255.",
        file=sys.stderr,
    )


def cmd_discover(args: argparse.Namespace) -> int:
    client = NsdpClient(timeout=args.timeout, broadcast=args.broadcast)
    switches = client.discover()
    if not switches:
        _no_reply_hint()
        return 1
    for i, info in enumerate(switches, 1):
        print(f"--- switch {i} ---")
        _print_info(info)
    return 0


def _single_client(args: argparse.Namespace) -> NsdpClient:
    return NsdpClient(timeout=args.timeout, broadcast=args.broadcast)


def cmd_info(args: argparse.Namespace) -> int:
    try:
        info = _single_client(args).get_info(device_ip=args.ip)
    except NsdpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        _no_reply_hint()
        return 1
    _print_info(info)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    try:
        version = _single_client(args).get_version(device_ip=args.ip)
    except NsdpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(version or "(firmware version not reported)")
    return 0


def cmd_ports(args: argparse.Namespace) -> int:
    try:
        speeds = _single_client(args).get_port_speeds(device_ip=args.ip)
    except NsdpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for ps in sorted(speeds, key=lambda p: p.port):
        print(f"  port {ps.port}: {ps.label}")
    return 0


def cmd_vlans(args: argparse.Namespace) -> int:
    try:
        vlans = _single_client(args).get_vlans_8021q(device_ip=args.ip)
    except NsdpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for v in sorted(vlans, key=lambda x: x.vlan_id):
        tagged = ",".join(map(str, v.tagged_ports)) or "-"
        untagged = ",".join(map(str, v.untagged_ports)) or "-"
        print(f"  vlan {v.vlan_id}: tagged={tagged} untagged={untagged}")
    return 0


def cmd_pvids(args: argparse.Namespace) -> int:
    try:
        pvids = _single_client(args).get_pvids(device_ip=args.ip)
    except NsdpError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for port, vlan_id in sorted(pvids.items()):
        print(f"  port {port}: pvid {vlan_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gs105e",
        description="Read-only NSDP client for NETGEAR GS105Ev2-class switches.",
    )
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT, help="reply wait (s)"
    )
    parser.add_argument(
        "--broadcast",
        default="255.255.255.255",
        help="broadcast address for discovery / targetless reads",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("discover", help="broadcast and list responding switches")

    for name, func, helptext in [
        ("info", cmd_info, "full device info"),
        ("version", cmd_version, "firmware version"),
        ("ports", cmd_ports, "per-port link speed/status"),
        ("vlans", cmd_vlans, "802.1Q VLAN membership"),
        ("pvids", cmd_pvids, "per-port default VLAN (PVID)"),
    ]:
        p = sub.add_parser(name, help=helptext)
        p.add_argument(
            "--ip",
            default=None,
            help="target switch IP (default: broadcast to the subnet)",
        )
        p.set_defaults(func=func)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "discover":
        return cmd_discover(args)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
