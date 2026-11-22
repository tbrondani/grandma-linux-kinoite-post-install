#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
GRANDMA_MESSAGE_LANG=en
DRY_RUN=0
UPGRADE=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --update) UPGRADE=1 ;;
        --lang=en|--lang=en-US) GRANDMA_MESSAGE_LANG=en ;;
        --lang=pt-BR) GRANDMA_MESSAGE_LANG=pt-BR ;;
        --help) printf 'Usage: ./setup.sh [--dry-run] [--update] [--lang=en|pt-BR]\n'; exit 0 ;;
        *) printf 'Unknown option: %s\n' "$arg" >&2; exit 2 ;;
    esac
done
source "$ROOT/scripts/common.sh"
source "$ROOT/scripts/system.sh"
source "$ROOT/scripts/apps.sh"
if (( DRY_RUN )); then
    say 'Preview only. No changes will be made.' 'Prévia. Nenhuma alteração será feita.'
else
    check_system
fi
install_system
install_apps
desktop_args=()
if (( DRY_RUN )); then desktop_args+=(--dry-run); fi
if [[ ${GRANDMA_ACCESSIBILITY:-1} == 1 ]]; then python3 "$ROOT/scripts/reading.py" "${desktop_args[@]}"; fi
if [[ ${GRANDMA_TRANSLATOR:-1} == 1 ]]; then python3 "$ROOT/scripts/translator.py" "${desktop_args[@]}"; fi
if (( UPGRADE )); then
    python3 "$ROOT/scripts/desktop.py" "${desktop_args[@]}" --update
    if [[ ${GRANDMA_THEME:-1} == 1 ]]; then python3 "$ROOT/scripts/theme.py" "${desktop_args[@]}"; fi
else
    python3 "$ROOT/scripts/desktop.py" "${desktop_args[@]}"
fi
if (( ! UPGRADE )); then
    python3 "$ROOT/scripts/settings.py" "${desktop_args[@]}"
else
    desktop_args+=(--update)
fi
python3 "$ROOT/scripts/user_tools_setup.py" "${desktop_args[@]}"
# Data installers share only the dry-run option.
desktop_args=()
if (( DRY_RUN )); then desktop_args+=(--dry-run); fi
if [[ ${GRANDMA_DICTIONARIES:-1} == 1 ]]; then python3 "$ROOT/scripts/dictionaries.py" "${desktop_args[@]}"; fi
if [[ ${GRANDMA_OFFLINE_MAPS:-1} == 1 ]]; then python3 "$ROOT/scripts/maps.py" "${desktop_args[@]}"; fi
say 'Application setup complete.' 'Configuração de aplicativos concluída.'

if [[ ${GRANDMA_OFFLINE_MAPS:-1} == 1 ]]; then say 'Portugal maps are ready. Restart Maps after setup. See docs/OFFLINE.md.' 'Os mapas de Portugal estão prontos. Reabra Mapas após a configuração. Veja docs/OFFLINE.pt-BR.md.'; fi


