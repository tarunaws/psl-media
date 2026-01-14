#!/usr/bin/env python3
"""Build an offline wheelhouse for this repo.

Run this on a machine/network that can download from PyPI (files.pythonhosted.org).
Best results come from running on the *same OS/CPU/Python* as the target machine.

Example (macOS arm64, Python 3.13):
  python3.13 code/scripts/build_wheelhouse.py --output-dir code/.wheelhouse

Then copy/zip `code/.wheelhouse/` onto the blocked machine and install via:
  code/.venv/bin/python3 code/scripts/install_wheelhouse.py --wheelhouse code/.wheelhouse
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WHEELHOUSE = PROJECT_ROOT / ".wheelhouse"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Download wheels into an offline wheelhouse.")
    parser.add_argument(
        "--requirements",
        default=str(PROJECT_ROOT / "requirements.txt"),
        help="Path to requirements file (default: code/requirements.txt)",
    )
    parser.add_argument(
        "--optional-ml",
        action="store_true",
        help="Also download wheels for code/requirements-optional-ml.txt",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_WHEELHOUSE),
        help="Directory to store downloaded wheels (default: code/.wheelhouse)",
    )
    parser.add_argument(
        "--allow-source",
        action="store_true",
        help="Allow source distributions if wheels are unavailable (may require build toolchain).",
    )

    args = parser.parse_args()

    requirements_path = Path(args.requirements).resolve()
    if not requirements_path.exists():
        raise SystemExit(f"requirements file not found: {requirements_path}")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    base_cmd = [python, "-m", "pip", "download", "--dest", str(output_dir), "-r", str(requirements_path)]

    # Prefer wheels because the blocked machine likely can't compile sdists.
    if not args.allow_source:
        base_cmd += ["--only-binary", ":all:"]

    # Keep pip output readable.
    env = os.environ.copy()
    env.setdefault("PIP_DISABLE_PIP_VERSION_CHECK", "1")

    print(f"Using python: {python}")
    print(f"Wheelhouse: {output_dir}")

    print("\nDownloading baseline requirements...")
    try:
        subprocess.run(base_cmd, check=True, env=env)
    except subprocess.CalledProcessError as exc:
        print("\nWheel download failed.")
        print(
            "Common causes:\n"
            "- A dependency has no prebuilt wheel for your platform/Python (macOS arm64 + Python 3.13).\n"
            "- Network blocks to files.pythonhosted.org (run this on an unblocked network).\n"
            "\nNext steps:\n"
            "- Re-run with --allow-source if you are OK building from source (requires build tools).\n"
            "- Or temporarily comment out optional packages in code/requirements.txt that lack wheels.\n"
        )
        return exc.returncode

    if args.optional_ml:
        opt = PROJECT_ROOT / "requirements-optional-ml.txt"
        if opt.exists():
            print("\nDownloading optional ML requirements...")
            cmd = [python, "-m", "pip", "download", "--dest", str(output_dir), "-r", str(opt)]
            if not args.allow_source:
                cmd += ["--only-binary", ":all:"]
            try:
                subprocess.run(cmd, check=True, env=env)
            except subprocess.CalledProcessError as exc:
                print("\nOptional ML wheel download failed.")
                print(
                    "This is expected if torch/onnxruntime/etc don't have wheels for your exact setup.\n"
                    "You can omit --optional-ml unless you need those features.\n"
                )
                return exc.returncode

    print("\nDone.")
    print("Next on the blocked machine:")
    print(f"  code/.venv/bin/python3 code/scripts/install_wheelhouse.py --wheelhouse {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
