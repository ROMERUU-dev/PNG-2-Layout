from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from png2vlsi.desktop_integration import install_launcher_entries


def main() -> int:
    installed = install_launcher_entries()
    for path in installed:
        print(f"Installed {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
