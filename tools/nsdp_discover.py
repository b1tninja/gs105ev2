"""Zero-install NSDP discovery probe (thin wrapper over the gs105e package).

Read-only: broadcasts an NSDP discovery query and prints responding
switches. The real implementation lives in the ``gs105e`` package
(``src/gs105e/``); this script just puts ``src/`` on ``sys.path`` so the
probe runs without ``pip install``, the way the sibling mfc9330cdw project
adds its snmpy checkout. For the full client (status, VLANs, versions) use
``python -m gs105e.cli`` after ``pip install -e .``.

Scope and caveats (NSDP removed on firmware 1.6.0.15+, etc.) are documented
in ``../docs/NSDP-PROTOCOL.md`` and ``../SECURITY.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir():
    sys.path.insert(0, str(_SRC))

from gs105e.cli import main  # noqa: E402

_SUBCOMMANDS = {"discover", "info", "version", "ports", "vlans", "pvids"}

if __name__ == "__main__":
    # Default to the discover subcommand. Top-level options (--timeout,
    # --broadcast) come before the subcommand, so append "discover" at the
    # end when the caller gave options but no explicit subcommand.
    argv = sys.argv[1:]
    if not any(arg in _SUBCOMMANDS for arg in argv):
        argv = [*argv, "discover"]
    raise SystemExit(main(argv))
