#!/usr/bin/env bash
# What a new machine hits when it tries to install SAP's PyRFC today.
#
# Run in a throwaway container so nothing already on the host can make it look
# easier than it is: no SDK, no wheels, no pip cache.
#
#   ./01_the_wall.sh
#
# Every command is real and every failure is the one pip actually prints.
set -u
IMAGE="${IMAGE:-python:3.12-slim}"

docker run --rm -i "$IMAGE" bash -s <<'INSIDE'
set -u
export PIP_DISABLE_PIP_VERSION_CHECK=1
step() { printf '\n\033[1m$ %s\033[0m\n' "$*"; }

step "pip install pyrfc"
# Every release was yanked when SAP archived the project, so nothing is left to
# resolve. pip names all nineteen.
pip install pyrfc 2>&1 | grep -iE 'yanked versions|No matching distribution'

step "why?  (PyPI's own reason for the yank)"
python - <<'PY'
import json, urllib.request
url = "https://pypi.org/pypi/pyrfc/3.3.1/json"
data = json.load(urllib.request.urlopen(url))
print(data["urls"][0]["yanked_reason"])
PY

step "pip install pyrfc==3.3.1        # ask for the last release by name"
# A pinned yanked version is still installable, so this gets further. There is
# no Linux wheel -- 3.3.1 shipped macOS arm64 and Windows only -- so pip falls
# back to the sdist and tries to compile it against SAP's closed-source RFC SDK.
pip install pyrfc==3.3.1 2>&1 | grep -A1 'SAPNWRFC_HOME not set'

step "pip install erpl-pyrfc"
pip install -q --root-user-action=ignore erpl-pyrfc

step "python -c 'import pyrfc; print(pyrfc.__version__)'"
python -c 'import pyrfc; print(pyrfc.__version__)'
INSIDE
