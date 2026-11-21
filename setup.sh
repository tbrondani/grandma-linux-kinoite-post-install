#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
LANGUAGE=en
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --lang=en|--lang=en-US) LANGUAGE=en ;;
        --lang=pt-BR) LANGUAGE=pt-BR ;;
        --help) printf 'Usage: ./setup.sh [--dry-run] [--lang=en|pt-BR]\n'; exit 0 ;;
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
python3 "$ROOT/scripts/translator.py" "${desktop_args[@]}"
python3 "$ROOT/scripts/desktop.py" "${desktop_args[@]}"
python3 "$ROOT/scripts/settings.py" "${desktop_args[@]}"
python3 "$ROOT/scripts/user_tools_setup.py" "${desktop_args[@]}"
python3 "$ROOT/scripts/dictionaries.py" "${desktop_args[@]}"
python3 "$ROOT/scripts/maps.py" "${desktop_args[@]}"
say 'Initial application setup complete. See docs/STATUS.md for pending features.' 'Configuração inicial de aplicativos concluída. Veja docs/STATUS.md para os recursos pendentes.'

say 'Portugal maps are ready. Restart Maps after setup. See docs/OFFLINE.md.' 'Os mapas de Portugal estão prontos. Reabra Mapas após a configuração. Veja docs/OFFLINE.pt-BR.md.'
