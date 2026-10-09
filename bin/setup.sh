#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"

echo "== MedFlow Setup =="

PYTHON_BIN="$(command -v python3 || command -v python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    echo "Setup requires python3 (or python on Windows), but neither was found in PATH." >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "Setup requires npm, but it was not found in PATH." >&2
    exit 1
fi
if ! "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
    echo "Setup requires the Python venv module, but it is unavailable." >&2
    exit 1
fi

cd "$REPO_ROOT"

if [[ ! -d ".venv" ]]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv .venv
fi

if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
elif [[ -f ".venv/Scripts/activate" ]]; then
    source .venv/Scripts/activate
else
    echo "The existing .venv has no supported activation script; repair or remove it before setup." >&2
    exit 1
fi

python -m pip install -r backend/requirements.txt

if [[ ! -e ".env" && ! -L ".env" ]]; then
    if [[ -f "backend/.env.example" ]]; then
        echo "Creating .env from backend/.env.example. Review it before running the application."
        cp backend/.env.example .env
    else
        echo "No .env or backend/.env.example found; configuration must be provided in the environment." >&2
        exit 1
    fi
else
    echo "Keeping existing .env unchanged."
fi

cd "$REPO_ROOT/frontend"
npm install

echo "Setup complete."
