"""Helpers to load layered .env files for local development."""
from __future__ import annotations

from typing import Optional

try:
    from dotenv import find_dotenv, load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    find_dotenv = None  # type: ignore[assignment]
    load_dotenv = None  # type: ignore[assignment]


def _load_file(filename: str, *, override: bool) -> bool:
    if not load_dotenv or not find_dotenv:
        return False
    path = find_dotenv(filename=filename, raise_error_if_not_found=False, usecwd=True)
    if not path:
        return False
    return bool(load_dotenv(path, override=override))


def load_environment() -> bool:
    """Load shared `.env` first, then override with `.env.local` if present."""
    if not load_dotenv or not find_dotenv:
        return False
    loaded = False
    loaded = _load_file(".env", override=False) or loaded
    loaded = _load_file(".env.local", override=True) or loaded
    return loaded
