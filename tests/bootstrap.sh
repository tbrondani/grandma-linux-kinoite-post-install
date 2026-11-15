#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
mkdir -p "$work/bin" "$work/project"
cat > "$work/project/setup.sh" <<'SCRIPT'
#!/usr/bin/env bash
printf '%s\n' "$@"
SCRIPT
tar -czf "$work/fixture.tar.gz" -C "$work" project
cat > "$work/bin/curl" <<'SCRIPT'
#!/usr/bin/env bash
set -eu
[[ ${FAIL_DOWNLOAD:-0} != 1 ]] || exit 22
while (( $# )); do
    if [[ $1 == --output ]]; then cp "$FIXTURE" "$2"; exit; fi
    shift
done
exit 1
SCRIPT
chmod +x "$work/bin/curl"
export FIXTURE="$work/fixture.tar.gz"
export PATH="$work/bin:$PATH"
output=$(bash "$ROOT/install.sh" --dry-run --lang=pt-BR)
[[ $output == $'--dry-run\n--lang=pt-BR' ]]
output=$(cat "$ROOT/install.sh" | bash -s -- --dry-run)
[[ $output == --dry-run ]]
if FAIL_DOWNLOAD=1 bash "$ROOT/install.sh" >/dev/null 2>&1; then exit 1; fi
if GRANDMA_REF='../bad' bash "$ROOT/install.sh" >/dev/null 2>&1; then exit 1; fi
printf 'PASS: bootstrap download, piped execution, arguments, download failure, invalid reference\n'
