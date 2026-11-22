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
printf '%s\n' "$GRANDMA_BOOTSTRAP_REF" > "$SELECTED_REF"
SCRIPT
tar -czf "$work/fixture.tar.gz" -C "$work" project
cat > "$work/bin/curl" <<'SCRIPT'
#!/usr/bin/env bash
set -eu
[[ ${FAIL_DOWNLOAD:-0} != 1 ]] || exit 22
printf '%s\n' "$*" >> "$CURL_CALLS"
if [[ $* == *'/releases/latest'* ]]; then
    printf '%s' "${LATEST_REDIRECT:-https://github.com/tbrondani/grandma-linux-kinoite-post-install/releases/tag/v0.1.0}"
    exit 0
fi
while (( $# )); do
    if [[ $1 == --output ]]; then cp "$FIXTURE" "$2"; exit; fi
    shift
done
exit 1
SCRIPT
chmod +x "$work/bin/curl"
export SELECTED_REF="$work/selected-ref" CURL_CALLS="$work/curl-calls"
export FIXTURE="$work/fixture.tar.gz"
export PATH="$work/bin:$PATH"
output=$(bash "$ROOT/install.sh" --dry-run --lang=pt-BR)
[[ $output == $'--dry-run\n--lang=pt-BR' ]]
output=$(cat "$ROOT/install.sh" | bash -s -- --dry-run)
[[ $output == --dry-run ]]
[[ $(cat "$SELECTED_REF") == v0.1.0 ]]
: > "$CURL_CALLS"
GRANDMA_REF=v0.1.0 bash "$ROOT/install.sh" --dry-run >/dev/null
[[ $(cat "$SELECTED_REF") == v0.1.0 ]]
! grep -q '/releases/latest' "$CURL_CALLS"
[[ $(cat "$CURL_CALLS") == *'/archive/v0.1.0.tar.gz'* ]]
GRANDMA_REF=main bash "$ROOT/install.sh" --dry-run >/dev/null
[[ $(cat "$SELECTED_REF") == main ]]
GRANDMA_REF=latest bash "$ROOT/install.sh" --dry-run >/dev/null
[[ $(cat "$SELECTED_REF") == v0.1.0 ]]
for redirect in 'https://example.invalid/releases/tag/v0.1.0' 'https://github.com/tbrondani/grandma-linux-kinoite-post-install/releases/tag/v0.2.0-rc1'; do
    if LATEST_REDIRECT="$redirect" bash "$ROOT/install.sh" >/dev/null 2>&1; then exit 1; fi
done
if FAIL_DOWNLOAD=1 bash "$ROOT/install.sh" >/dev/null 2>&1; then exit 1; fi
if GRANDMA_REF='../bad' bash "$ROOT/install.sh" >/dev/null 2>&1; then exit 1; fi
mkdir -p "$work/home/.local/bin"
cat > "$work/home/.local/bin/grandma-update" <<'SCRIPT'
#!/usr/bin/env bash
[[ $1 == --check ]] || exit 2
printf 'Update check only\n'
SCRIPT
chmod +x "$work/home/.local/bin/grandma-update"
: > "$CURL_CALLS"
output=$(HOME="$work/home" bash "$ROOT/install.sh" --check)
[[ $output == 'Update check only' && ! -s $CURL_CALLS ]]
if HOME="$work/not-installed" bash "$ROOT/install.sh" --check >/dev/null 2>&1; then exit 1; fi
printf 'PASS: bootstrap download, piped execution, arguments, download failure, invalid reference\n'
