#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Keep all work inside a function so a truncated download cannot start installation.
bootstrap() (
    set -Eeuo pipefail
    local ref=${GRANDMA_REF:-main}
    local archive_url tmp tool
    [[ $ref =~ ^[a-zA-Z0-9][a-zA-Z0-9._/-]*$ && $ref != *..* ]] || {
        printf 'Invalid GRANDMA_REF\n' >&2; exit 2;
    }
    for tool in curl tar mktemp bash; do
        command -v "$tool" >/dev/null || { printf 'Required command: %s\n' "$tool" >&2; exit 1; }
    done
    tmp=$(mktemp -d)
    trap 'rm -rf -- "$tmp"' EXIT
    archive_url="https://github.com/tbrondani/grandma-linux-kinoite-post-install/archive/${ref}.tar.gz"
    curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        "$archive_url" --output "$tmp/source.tar.gz"
    mkdir "$tmp/source"
    tar -xzf "$tmp/source.tar.gz" --strip-components=1 -C "$tmp/source"
    [[ -f $tmp/source/setup.sh ]] || { printf 'Archive does not contain setup.sh\n' >&2; exit 1; }
    # Reserve stdin for authorization and other interactive tools when piped from curl.
    if [[ -t 0 ]]; then
        bash "$tmp/source/setup.sh" "$@"
    elif [[ -r /dev/tty ]] && ( : < /dev/tty ) 2>/dev/null; then
        bash "$tmp/source/setup.sh" "$@" < /dev/tty
    else
        bash "$tmp/source/setup.sh" "$@" < /dev/null
    fi
)
bootstrap "$@"
