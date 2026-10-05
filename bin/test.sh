#!/usr/bin/env bash
# MedFlow test runner: activates the venv and runs the pytest suite.
#
# Run from the medflow folder:
#   bash bin/test.sh

set -euo pipefail

echo "== MedFlow Test Runner =="

cd "$(dirname "$0")/.."

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source .venv/Scripts/activate
fi

echo "Running tests..."
python -m pytest backend -v

echo "Test run complete."