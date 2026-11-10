"""Build the standalone Windows executable with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Create ``dist/odds-ticker.exe`` and bundle the Textual stylesheet."""
    separator = ";" if sys.platform == "win32" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--paths",
        str(ROOT),
        "--name",
        "odds-ticker",
        "--add-data",
        f"{ROOT / 'odds_ticker' / 'styles.tcss'}{separator}odds_ticker",
        str(ROOT / "odds_ticker" / "app.py"),
    ]
    subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
