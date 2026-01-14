#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


URL_RE = re.compile(r"https://files\.pythonhosted\.org/[^\s\)\"]+")


def run(cmd: list[str], *, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def extract_pythonhosted_urls(output: str) -> list[str]:
    urls = URL_RE.findall(output)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    if not name:
        raise ValueError(f"Could not determine filename from url: {url}")
    return name


def curl_download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    # A slightly browser-like UA helps in some environments.
    cmd = [
        "curl",
        "-fL",
        "-A",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
        url,
        "-o",
        str(dest),
    ]
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"curl failed for {url}\n{proc.stdout}")


def pip_install(args: list[str], *, cwd: str) -> subprocess.CompletedProcess[str]:
    return run([sys.executable, "-m", "pip", *args], cwd=cwd)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    requirements_path = project_root / "requirements.txt"
    wheelhouse_dir = project_root / ".wheelhouse"

    if not requirements_path.exists():
        print(f"ERROR: requirements file not found: {requirements_path}")
        return 2

    if shutil.which("curl") is None:
        print("ERROR: curl is required but not found on PATH")
        return 2

    print(f"Using python: {sys.executable}")
    print(f"Requirements: {requirements_path}")
    print(f"Wheelhouse: {wheelhouse_dir}")

    # Keep trying until pip succeeds, downloading any 403-blocked artifacts via curl.
    max_rounds = int(os.environ.get("PIP_CURL_FALLBACK_MAX_ROUNDS", "200"))
    cwd = str(project_root)

    for round_idx in range(1, max_rounds + 1):
        print(f"\n=== Round {round_idx}/{max_rounds}: pip install -r requirements.txt ===")
        proc = pip_install([
            "install",
            "-r",
            str(requirements_path),
            "--index-url",
            "https://pypi.org/simple",
        ], cwd=cwd)

        if proc.returncode == 0:
            print("\n✅ pip install completed successfully")
            return 0

        output = proc.stdout or ""
        urls = extract_pythonhosted_urls(output)

        # If pip failed for a reason other than 403/pythonhosted download, bail out.
        if not urls or "403" not in output:
            print(output)
            print("\nERROR: pip failed for a non-pythonhosted-403 reason (or URL could not be extracted).")
            return proc.returncode or 1

        print("pip failed with 403 for these artifacts:")
        for u in urls:
            print(f"- {u}")

        # Download and install each missing artifact.
        for url in urls:
            filename = filename_from_url(url)
            dest = wheelhouse_dir / filename

            if dest.exists() and dest.stat().st_size > 0:
                print(f"Already downloaded: {dest.name}")
            else:
                print(f"Downloading via curl: {filename}")
                curl_download(url, dest)

            # Install the artifact directly to avoid pip fetching it.
            print(f"Installing from wheelhouse: {dest.name}")
            install_proc = pip_install(["install", "--no-index", str(dest)], cwd=cwd)
            if install_proc.returncode != 0:
                print(install_proc.stdout)
                print(f"\nERROR: Failed installing downloaded artifact: {dest}")
                return install_proc.returncode or 1

    print(f"\nERROR: exceeded max rounds ({max_rounds})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
