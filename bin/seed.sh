#!/usr/bin/env bash
# MedFlow seed: drops and recreates the tables, then loads the demo
# hospitals, users, equipment and work orders (backend/seed.py does all three).
#
# Run from the medflow folder:
#   bash bin/seed.sh          (local database, the default)
#   bash bin/seed.sh local
#   DATABASE_URL="postgresql+asyncpg://..." bash bin/seed.sh

set -euo pipefail

cd "$(dirname "$0")/.."

echo "Seeding database configured by DATABASE_URL or backend/app/config.py."
echo "Warning: this drops and recreates the database tables."

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source .venv/Scripts/activate
fi

# runs as a module from the repo root because seed.py imports backend.app...
python -m backend.seed

echo "Seed complete."