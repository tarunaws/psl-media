#!/usr/bin/env python3
"""Entry point for the Personalized Trailer service."""

from __future__ import annotations

import os

from personalized_trailer_service import app, create_app


def main() -> None:
	flask_app = app if app is not None else create_app()
	port = int(os.getenv("PERSONALIZED_TRAILER_PORT", "5007"))
	flask_app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
	main()
