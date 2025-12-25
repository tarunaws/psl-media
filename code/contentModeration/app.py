import os

from content_moderation_service import app


if __name__ == "__main__":  # pragma: no cover - convenience launcher
    port = int(os.getenv("CONTENT_MODERATION_API_PORT", "5006"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
