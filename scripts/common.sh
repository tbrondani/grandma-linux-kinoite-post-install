#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
say() {
    if [[ ${GRANDMA_MESSAGE_LANG:-${LANGUAGE:-en}} == pt-BR ]]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi
}
run() {
    if (( DRY_RUN )); then printf '  '; printf '%q ' "$@"; printf '\n'; else "$@"; fi
}
fail() { say "$1" "$2" >&2; exit 1; }
