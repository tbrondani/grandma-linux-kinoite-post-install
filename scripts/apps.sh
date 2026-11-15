#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
install_apps() {
    local id native en pt
    local -a missing=()
    while IFS='|' read -r id native en pt; do
        [[ -n $id && $id != \#* ]] || continue
        if (( ! DRY_RUN )); then
            # Preserve existing native or user/system Flatpak installations.
            if [[ $native != - ]] && command -v "$native" >/dev/null; then continue; fi
            if flatpak info --user "$id" >/dev/null 2>&1 || flatpak info --system "$id" >/dev/null 2>&1; then continue; fi
        fi
        missing+=("$id")
    done < "$ROOT/data/apps.tsv"
    (( ${#missing[@]} )) || return 0
    run flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    if (( ! DRY_RUN )); then
        # Verify every app before starting the install transaction. Fail on a disabled or unavailable remote.
        for id in "${missing[@]}"; do flatpak remote-info --user flathub "$id" >/dev/null; done
    fi
    run flatpak install --user -y flathub "${missing[@]}"
}
