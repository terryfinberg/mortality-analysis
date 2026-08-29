#!/usr/bin/env bash
# Bootstrap for macOS / Linux / WSL
set -euo pipefail
cd "$(dirname "$0")"

echo "=== A Fragile Equilibrium: environment bootstrap ==="

PY=""
for c in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "ERROR: Python not found. Install Python 3.10+." >&2; exit 1; }

echo "Python $($PY -c 'import sys; print(".".join(map(str,sys.version_info[:2])))') at $(command -v $PY)"

if [ ! -d .venv ]; then
    echo "Creating virtual environment..."
    "$PY" -m venv .venv
else
    echo "Reusing existing .venv"
fi

VPY=".venv/bin/python"

echo "Installing dependencies..."
"$VPY" -m pip install --upgrade pip --quiet
"$VPY" -m pip install -r requirements.txt --quiet

echo "Registering Jupyter kernel..."
"$VPY" -m ipykernel install --user --name fragile-equilibrium \
    --display-name "Python (fragile-equilibrium)" >/dev/null

echo "Running tests..."
"$VPY" -m pytest -q

cat <<'MSG'

=== Bootstrap complete ===

The data files in data/raw/ are empty by design.
Populate them from data/queries/cdc_wonder_queries.md, then run:
    .venv/bin/python -m src.report

See UAT_CHECKLIST.md for the step-by-step path.
MSG
