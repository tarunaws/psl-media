import json
import os
import threading
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_VISIBILITY_FILE = os.getenv(
    'USECASE_VISIBILITY_FILE',
    os.path.join(PROJECT_ROOT, 'config', 'usecase-visibility.json')
)

_file_lock = threading.Lock()


def _ensure_directory_exists(path: str) -> None:
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _load_state() -> dict:
    if not os.path.exists(DEFAULT_VISIBILITY_FILE):
        return {"hidden": [], "updatedAt": None}

    try:
        with _file_lock, open(DEFAULT_VISIBILITY_FILE, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {"hidden": [], "updatedAt": None}

    hidden = data.get('hidden') or []
    if not isinstance(hidden, list):
        hidden = []

    normalized = []
    seen = set()
    for item in hidden:
        if isinstance(item, str):
            if item not in seen:
                normalized.append(item)
                seen.add(item)

    return {
        "hidden": normalized,
        "updatedAt": data.get('updatedAt')
    }


def _write_state(hidden_ids):
    sanitized = []
    seen = set()
    for item in hidden_ids:
        if isinstance(item, str) and item not in seen:
            sanitized.append(item)
            seen.add(item)

    state = {
        "hidden": sanitized,
        "updatedAt": datetime.now(timezone.utc).isoformat()
    }

    _ensure_directory_exists(DEFAULT_VISIBILITY_FILE)
    with _file_lock, open(DEFAULT_VISIBILITY_FILE, 'w', encoding='utf-8') as handle:
        json.dump(state, handle, indent=2)

    return state


@app.get('/health')
def health_check():
    return jsonify({
        "status": "ok",
        "service": "usecase-visibility",
        "file": DEFAULT_VISIBILITY_FILE
    })


@app.get('/visibility')
def get_visibility():
    return jsonify(_load_state())


@app.post('/visibility')
def update_visibility():
    payload = request.get_json(silent=True) or {}
    hidden = payload.get('hidden')
    if hidden is None:
        return jsonify({
            "error": "Request body must include a 'hidden' array of use-case IDs."
        }), 400

    if not isinstance(hidden, list):
        return jsonify({
            "error": "'hidden' must be an array of strings."
        }), 400

    state = _write_state(hidden)
    return jsonify(state), 200


if __name__ == '__main__':
    port = int(os.getenv('USECASE_VISIBILITY_PORT', '5012'))
    app.run(host='0.0.0.0', port=port)
