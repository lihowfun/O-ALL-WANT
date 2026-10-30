#!/usr/bin/env bash
# Compatibility entry point. All validation and writes live in the Python CLI.
set -euo pipefail
FRAMEWORK_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PYTHON=""
if [[ -n "${OAW_PYTHON:-}" ]]; then
    if "$OAW_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
        PYTHON="$OAW_PYTHON"
    else
        echo "OAW_PYTHON must name a working Python 3.10+ interpreter." >&2
        exit 2
    fi
else
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
            PYTHON="$candidate"
            break
        fi
    done
fi
if [[ -z "$PYTHON" ]]; then
    echo "Python 3.10+ is required. Install it or set OAW_PYTHON." >&2
    exit 2
fi
case "${1:-}" in
    init|migrate|doctor) exec "$PYTHON" "$FRAMEWORK_DIR/scripts/oaw.py" "$@" ;;
    *) exec "$PYTHON" "$FRAMEWORK_DIR/scripts/oaw.py" init --target "$PWD" "$@" ;;
esac
