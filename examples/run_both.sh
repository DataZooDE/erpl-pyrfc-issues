#!/usr/bin/env bash
# Run `02_same_script.py` under SAP's PyRFC and under erpl-pyrfc, and diff.
#
# The two libraries never meet: each gets its own virtualenv, and only one of
# them is on `sys.path` at a time. What is shared is the script, the ABAP
# system, and the environment it reads its credentials from.
#
#   SAPNWRFC_HOME=/path/to/nwrfcsdk SAP_USER=... SAP_PASSWD=... ./run_both.sh
#
# `SAPNWRFC_HOME` is the SAP NW RFC SDK, needed to *build* PyRFC 3.3.1 -- there
# is no Linux wheel. Without it this script says so and stops, rather than
# quietly comparing one library against itself.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${WORK:-${TMPDIR:-/tmp}/pyrfc-side-by-side}"
: "${SAPNWRFC_HOME:?set SAPNWRFC_HOME to the SAP NW RFC SDK (needed to build PyRFC 3.3.1)}"

mkdir -p "$WORK"

# -- SAP's PyRFC, built from the yanked sdist against the SDK ---------------
if [ ! -x "$WORK/sap/bin/python" ]; then
    echo "== building SAP PyRFC 3.3.1 from source (a few minutes) =="
    python3 -m venv "$WORK/sap"
    "$WORK/sap/bin/pip" -q install --upgrade pip setuptools wheel cython
    SAPNWRFC_HOME="$SAPNWRFC_HOME" \
        "$WORK/sap/bin/pip" install --no-binary :all: pyrfc==3.3.1
fi

# -- erpl-pyrfc, from PyPI, with nothing else ------------------------------
#
# `ERPL_VENV` points this at a working tree instead, for checking a change
# before it is released. Whichever is used gets printed, so a run can never be
# mistaken for the other.
if [ -n "${ERPL_VENV:-}" ]; then
    ERPL_PYTHON="$ERPL_VENV/bin/python"
else
    if [ ! -x "$WORK/erpl/bin/python" ]; then
        echo "== installing erpl-pyrfc from PyPI =="
        python3 -m venv "$WORK/erpl"
        "$WORK/erpl/bin/pip" -q install erpl-pyrfc
    fi
    ERPL_PYTHON="$WORK/erpl/bin/python"
fi

echo
# The SDK's shared libraries have to be on the path even to import it.
SAP_VERSION=$(LD_LIBRARY_PATH="$SAPNWRFC_HOME/lib" "$WORK/sap/bin/python" -c 'import pyrfc; print(pyrfc.__version__)')
echo "== SAP PyRFC $SAP_VERSION (needs $SAPNWRFC_HOME on LD_LIBRARY_PATH) =="
LD_LIBRARY_PATH="$SAPNWRFC_HOME/lib" "$WORK/sap/bin/python" "$HERE/02_same_script.py" > "$WORK/sap.txt"
tail -5 "$WORK/sap.txt"

echo
echo "== erpl-pyrfc $("$ERPL_PYTHON" -c 'import pyrfc; print(pyrfc.__version__)') (no SDK, no library path) =="
"$ERPL_PYTHON" "$HERE/02_same_script.py" > "$WORK/erpl.txt"
tail -5 "$WORK/erpl.txt"

echo
echo "== diff =="
if diff "$WORK/sap.txt" "$WORK/erpl.txt"; then
    printf '\033[1mno differences across %s lines\033[0m\n' "$(wc -l < "$WORK/sap.txt")"
else
    echo "the two libraries disagree (above)"
    exit 1
fi
