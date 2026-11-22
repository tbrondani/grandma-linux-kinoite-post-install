#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec python3 "$ROOT/scripts/installer.py" "$@"
