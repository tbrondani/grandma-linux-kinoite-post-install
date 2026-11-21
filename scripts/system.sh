#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
check_system() {
    (( EUID != 0 )) || fail 'Run as your desktop user, without sudo.' 'Execute como seu usuário da área de trabalho, sem sudo.'
    source /etc/os-release
    [[ ${ID:-} == fedora && ${VARIANT_ID:-} == kinoite && $(uname -m) == x86_64 ]] ||
        fail 'This setup requires Fedora Kinoite x86_64.' 'Esta configuração exige Fedora Kinoite x86_64.'
    [[ ${XDG_CURRENT_DESKTOP:-} == *KDE* && ${XDG_SESSION_TYPE:-} == wayland ]] ||
        fail 'Run from a KDE Wayland session.' 'Execute em uma sessão KDE Wayland.'
    for tool in flatpak rpm rpm-ostree python3 plasmashell xdg-user-dir update-desktop-database kwriteconfig6 plasma-apply-desktoptheme plasma-apply-colorscheme gdbus kbuildsycoca6; do
        command -v "$tool" >/dev/null || fail "Missing tool: $tool" "Ferramenta ausente: $tool"
    done
    [[ $(plasmashell --version) == 'plasmashell 6.'* ]] ||
        fail 'KDE Plasma 6 is required.' 'É necessário usar KDE Plasma 6.'
    # A pending deployment must be booted before making more package changes.
    local deployment_status
    deployment_status=$(rpm-ostree status --json) || fail 'Cannot read deployment status.' 'Não foi possível consultar as implantações.'
    if python3 -c 'import json,sys; d=json.load(sys.stdin)["deployments"]; sys.exit(0 if d and not d[0].get("booted",False) else 1)' <<< "$deployment_status"; then
        say 'A deployment is pending. Reboot and run setup again.' 'Há uma implantação pendente. Reinicie e execute novamente.'
        exit 0
    fi
}
install_system() {
    local package
    local -a missing=()
    for package in vim-enhanced restic fastfetch b3sum kdialog python3-dbus python3-gobject-base; do
        if (( DRY_RUN )) || ! rpm -q "$package" >/dev/null 2>&1; then missing+=("$package"); fi
    done
    if (( ${#missing[@]} )); then
        if [[ ${GRANDMA_TEST_VM:-0} == 1 ]]; then
            run sudo -n rpm-ostree install "${missing[@]}"
        else
            run rpm-ostree install "${missing[@]}"
        fi
        if (( ! DRY_RUN )); then
            say 'Reboot, then run the same setup command again.' 'Reinicie e execute o mesmo comando de configuração.'
            exit 0
        fi
    fi
}
