#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
RESET=false
ASSUME_YES=false

usage() {
    cat <<'EOF'
Usage: bash bin/seed.sh [--reset] [--yes]

Create or update the MedFlow schema and demo records in the configured database.
  --reset  Also reset the seeded users' passwords to SEED_USER_PASSWORD.
  --yes    Skip the confirmation prompt (valid only with --reset).

Set DATABASE_URL and SEED_USER_PASSWORD in the environment or in the repository
root .env file. Values are never printed. The script requires psql.
EOF
}

while (($#)); do
    case "$1" in
        --reset)
            RESET=true
            ;;
        --yes)
            ASSUME_YES=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [[ "$ASSUME_YES" == true && "$RESET" != true ]]; then
    echo "--yes is only valid together with --reset." >&2
    exit 2
fi

cd "$REPO_ROOT"

if [[ -f ".venv/bin/activate" ]]; then
    source .venv/bin/activate
elif [[ -f ".venv/Scripts/activate" ]]; then
    source .venv/Scripts/activate
else
    echo "Python virtual environment not found. Run bash bin/setup.sh first." >&2
    exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
    echo "psql is required to apply db/sql/schema.sql and db/sql/seed.sql." >&2
    exit 1
fi

read_env_value() {
    local key="$1"
    python - "$REPO_ROOT/.env" "$key" <<'PY'
import sys
from dotenv import dotenv_values

values = dotenv_values(sys.argv[1])
value = values.get(sys.argv[2])
if value is not None:
    print(value)
PY
}

if [[ -z "${DATABASE_URL:-}" && -f ".env" ]]; then
    DATABASE_URL="$(read_env_value DATABASE_URL)"
    export DATABASE_URL
fi
if [[ -z "${SEED_USER_PASSWORD:-}" && -f ".env" ]]; then
    SEED_USER_PASSWORD="$(read_env_value SEED_USER_PASSWORD)"
    export SEED_USER_PASSWORD
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL is required. Set it in the environment or repository root .env file." >&2
    exit 1
fi
if [[ -z "${SEED_USER_PASSWORD:-}" ]]; then
    echo "SEED_USER_PASSWORD is required. Set it in the environment or repository root .env file." >&2
    exit 1
fi

if [[ "$RESET" == true && "$ASSUME_YES" != true ]]; then
    echo "This will overwrite the seeded users' passwords with SEED_USER_PASSWORD."
    if [[ ! -t 0 ]]; then
        echo "Cannot confirm reset without an interactive terminal; rerun with --reset --yes if you intend to proceed." >&2
        exit 1
    fi
    printf "Continue? [y/N] "
    if ! IFS= read -r answer; then
        echo "Reset cancelled because confirmation could not be read." >&2
        exit 1
    fi
    case "${answer,,}" in
        y|yes) ;;
        *)
            echo "Reset cancelled."
            exit 1
            ;;
    esac
fi

SEED_PASSWORD_HASH="$(python -c 'import os; from backend.app.security import hash_password; print(hash_password(os.environ["SEED_USER_PASSWORD"]))')"
PSQL_DATABASE_URL="${DATABASE_URL/postgresql+asyncpg:/postgresql:}"

psql "$PSQL_DATABASE_URL" \
    -v ON_ERROR_STOP=1 \
    -f "$REPO_ROOT/db/sql/schema.sql"

if [[ "$RESET" == true ]]; then
    RESET_SEED=true
else
    RESET_SEED=false
fi

psql "$PSQL_DATABASE_URL" \
    -v ON_ERROR_STOP=1 \
    -v seed_password_hash="$SEED_PASSWORD_HASH" \
    -v reset_seed="$RESET_SEED" \
    -f "$REPO_ROOT/db/sql/seed.sql"

echo "Seed complete."
