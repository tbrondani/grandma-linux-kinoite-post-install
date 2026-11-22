#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
bash -n setup.sh install.sh scripts/*.sh tests/*.sh
bash tests/bootstrap.sh
python3 tests/test_desktop.py
python3 tests/test_theme.py
python3 tests/test_settings.py
python3 tests/test_reading.py
python3 tests/maps.py
python3 tests/test_user_tools.py
python3 tests/test_manual.py
python3 tests/test_project_update.py
python3 tests/test_release.py
python3 tests/test_vm_login.py
python3 tests/test_vm_runner.py
python3 tests/test_backup.py
./setup.sh --dry-run --lang=en >/dev/null
./setup.sh --dry-run --lang=pt-BR >/dev/null
if ./setup.sh --invalid >/dev/null 2>&1; then exit 1; fi
# Querying a version must not require a working graphical display.
(
    source scripts/common.sh
    source scripts/system.sh
    plasmashell() { [[ ${QT_QPA_PLATFORM:-} == offscreen ]] || return 134; printf 'plasmashell 6.8.3\n'; }
    check_plasma_version
)
# Exercise existing and missing application paths without installing anything.
ROOT=$PWD
LANGUAGE=en
DRY_RUN=0
source scripts/common.sh
source scripts/apps.sh
calls=0
flatpak() {
    case "$1" in
        info) return 0 ;;
        *) calls=$((calls + 1)) ;;
    esac
}
install_apps
[[ $calls == 0 ]] || { echo 'Existing applications triggered installation'; exit 1; }
flatpak() {
    case "$1" in
        info) return 1 ;;
        *) calls=$((calls + 1)) ;;
    esac
}
install_apps
(( calls > 2 )) || { echo 'Missing apps were not checked and installed'; exit 1; }
# A package operation must stop setup before app installation.
source scripts/system.sh
rpm() { return 1; }
run() { printf '%s\n' "$*"; }
result=$(install_system; printf 'ERROR: continued after package installation\n')
[[ $result == *'rpm-ostree install vim-enhanced restic'* && $result != *'ERROR:'* ]]
code=0
( UPGRADE=1; install_system ) >/dev/null || code=$?
[[ $code == 75 ]] || { echo 'Update package stage did not request a reboot'; exit 1; }
printf 'PASS: syntax, options, previews, duplicate handling, package reboot boundary\n'
