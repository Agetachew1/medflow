#!/usr/bin/env bash
# MedFlow setup: gets a fresh clone running with one command.
# Creates the .venv in the repo root if it doesn't exist, installs Python
# dependencies, creates backend/.env from the template if it exists,
# then installs the frontend dependencies. Safe to run more than once.
#
# Run from the medflow folder:
#   bash bin/setup.sh

set -euo pipefail

echo "== MedFlow Setup =="

# always run from the repo root, wherever the script was called from
cd "$(dirname "$0")/.."

# create the virtual environment if it doesn't already exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# activate it (Mac/Linux use bin/, Windows Git Bash uses Scripts/)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source .venv/Scripts/activate
fi

pip install -r backend/requirements.txt

# create backend/.env from the template if it doesn't exist yet
if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo "No backend/.env found - copying from backend/.env.example."
        echo "Review backend/.env before running the app."
        cp backend/.env.example backend/.env
    else
        echo "No backend/.env.example found; the app will use its configured defaults."
    fi
fi

# frontend setup
cd frontend
npm install

echo "Setup complete"