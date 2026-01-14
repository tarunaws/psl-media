#!/usr/bin/env python3
"""Install dependencies from an offline wheelhouse.

This is designed for environments where `pip` cannot download from
`files.pythonhosted.org` (e.g., corporate blocks).

Example:
  code/.venv/bin/python3 code/scripts/install_wheelhouse.py --wheelhouse code/.wheelhouse
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], env: dict[str, str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install requirements from a local wheelhouse.")
    parser.add_argument(
        "--wheelhouse",
        required=True,
        help="Path to wheelhouse directory (folder of .whl/.tar.gz files)",
    )
    parser.add_argument(
        "--requirements",
        default=str(PROJECT_ROOT / "requirements.txt"),
        help="Path to requirements file (default: code/requirements.txt)",
    )
    parser.add_argument(
        "--optional-ml",
        action="store_true",
        help="Also install code/requirements-optional-ml.txt",
    )

    args = parser.parse_args()

    wheelhouse = Path(args.wheelhouse).resolve()
    if not wheelhouse.exists() or not wheelhouse.is_dir():
        raise SystemExit(f"wheelhouse directory not found: {wheelhouse}")

    requirements_path = Path(args.requirements).resolve()
    if not requirements_path.exists():
        raise SystemExit(f"requirements file not found: {requirements_path}")

    python = sys.executable

    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")

    print(f"Using python: {python}")
    print(f"Wheelhouse: {wheelhouse}")

    # Install baseline requirements.
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "-r",
            str(requirements_path),
        ],
        env,
    )

    if args.optional_ml:
        opt = PROJECT_ROOT / "requirements-optional-ml.txt"
        if opt.exists():
            run(
                [
                    python,
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    str(wheelhouse),
                    "-r",
                    str(opt),
                ],
                env,
            )

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
