#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
VM_NAME=${VM_NAME:-fedora-kinoite-test-v2}
if [[ -n ${VM_CONFIG:-} ]]; then
    vm_values=$(python3 "$ROOT/scripts/vm/profile.py" "$VM_CONFIG")
    mapfile -t vm_values <<< "$vm_values"
    VM_USER=${VM_USER:-${vm_values[0]}}
    if [[ ${vm_values[1]} == 0 && ${FRESH:-1} == 1 ]]; then
        echo 'Use FRESH=0 for a new-VM profile without auto-login; clean-baseline preparation requires auto-login.' >&2; exit 2
    fi
fi
VM_USER=${VM_USER:-tester}
VM_HOST=${VM_HOST:-}
URI=${LIBVIRT_URI:-qemu:///system}
if [[ ${1:-} == --help ]]; then
    printf 'Usage: bash scripts/vm/start-test.sh\nDefault VM user: tester. Override VM_USER or VM_HOST if needed.\nRequires an installed VM, a logged-in KDE desktop, and sshd. SSH can ask for your password.\n'
    exit 0
fi
# Keep console output and a machine-readable result for unattended checks.
mkdir -p "$ROOT/test-results"
log=$(mktemp "$ROOT/test-results/deploy-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX.log")
summary="${log%.log}.json"
phase=preflight
TEST_UPDATE=${TEST_UPDATE:-0}
TEST_PROFILES=${TEST_PROFILES:-0}
[[ $TEST_PROFILES == 0 || $TEST_PROFILES == 1 ]] || exit 2
[[ $TEST_UPDATE == 0 || $TEST_UPDATE == 1 ]] || { echo 'TEST_UPDATE must be 0 or 1.' >&2; exit 2; }
remote_dir=''
declare -a ssh_options=()
exec > >(tee -a "$log") 2>&1
finish() {
    local code=$?
    trap - EXIT
    if declare -F cleanup >/dev/null; then cleanup; fi
    python3 - "$summary" "$code" "$phase" "$log" "$VM_NAME" "$remote_dir" <<'PYTHON'
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
path,code,phase,log,vm,guest=sys.argv[1:]
result=dict(finished_at=datetime.now(timezone.utc).isoformat(),exit_code=int(code),
            status='passed' if int(code)==0 else 'failed',
            phase=phase,log=log,vm=vm,guest_directory=guest)
Path(path).write_text(json.dumps(result,indent=2)+'\n')
PYTHON
    printf 'Deploy log: %s\nDeploy result: %s\n' "$log" "$summary"
    exit "$code"
}
trap finish EXIT
printf 'Deploy log: %s\n' "$log"
(( EUID != 0 )) || { echo 'Run this script as your desktop user, without sudo in front.' >&2; exit 2; }
[[ $VM_USER =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'Set VM_USER to the desktop user in the VM.' >&2; exit 2; }
for tool in virsh ssh scp tar python3; do command -v "$tool" >/dev/null || { echo "Missing: $tool" >&2; exit 1; }; done
if [[ $URI != qemu:///system ]]; then
    echo 'The test runner requires qemu:///system.' >&2; exit 2
fi
phase=host-authentication
host_work=$(mktemp -d)
host_report="$host_work/host.json"
(umask 077; : > "$host_report")
host_args=(--vm "$VM_NAME" --user "$VM_USER" --uri "$URI" --report "$host_report")
if [[ ${FRESH:-1} == 1 ]]; then host_args+=(--fresh); fi
if [[ -n $VM_HOST ]]; then host_args+=(--host "$VM_HOST"); fi
if [[ -n ${ISO_PATH:-} ]]; then host_args+=(--iso "$ISO_PATH"); fi
host_args+=(--fedora "${FEDORA_VERSION:-45}")
if [[ -n ${VM_CONFIG:-} ]]; then
    host_args+=(--locale "${vm_values[2]}")
    if [[ ${vm_values[1]} == 0 ]]; then host_args+=(--no-autologin); fi
fi
# A single sudo process owns the complete host phase. Child helpers run inside
# that authorized process, so neither ticket expiry nor PPID scope can re-prompt.
if ! sudo -- /usr/bin/python3 "$ROOT/scripts/vm/prepare-host.py" "${host_args[@]}"; then
    rm -rf -- "$host_work"; exit 1
fi
VM_HOST=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["host"])' "$host_report")
display=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["display"])' "$host_report")
rm -rf -- "$host_work"
# A separate libvirt GUI can trigger its own Polkit authentication. Keep it
# opt-in; an already open virt-manager display continues to work normally.
if [[ ${OPEN_VM_DISPLAY:-0} == 1 ]]; then
    if [[ -n $display ]] && command -v remote-viewer >/dev/null; then
        remote-viewer "$display" >/dev/null 2>&1 &
    elif command -v virt-manager >/dev/null; then
        echo 'The optional viewer may request its own graphical authorization.'
        virt-manager --connect "$URI" --show-domain-console "$VM_NAME" >/dev/null 2>&1 &
    fi
else
    echo 'Host preparation complete. Use the existing VM window for the visual review.'
fi
[[ $VM_HOST =~ ^[a-zA-Z0-9.:_-]+$ ]] || { echo 'Cannot discover VM address. Set VM_HOST explicitly.' >&2; exit 1; }
target="$VM_USER@$VM_HOST"
work=$(mktemp -d)
cleanup() {
    if (( ${#ssh_options[@]} )) && [[ -n ${target:-} ]]; then
        ssh "${ssh_options[@]}" -O exit "$target" >/dev/null 2>&1 || true
    fi
    rm -rf -- "$work"
}
mkdir -p "$ROOT/.vm-state/ssh-hosts"
ssh_options=(-F /dev/null -o "UserKnownHostsFile=$ROOT/.vm-state/ssh-hosts/$VM_NAME" -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new
    -o ControlMaster=auto -o ControlPersist=600 -o "ControlPath=$work/ssh-control")
if [[ -f $ROOT/.vm-state/test-key ]]; then
    ssh_options+=(-i "$ROOT/.vm-state/test-key" -o IdentitiesOnly=yes)
fi
wait_for_ssh() {
    echo "Waiting for SSH at $target. First OS installation can take several minutes."
    for ((attempt=0; attempt<900; attempt++)); do
        if (( attempt % 15 == 0 )); then echo "Still waiting for the VM SSH service (attempt $((attempt + 1))/900)..."; fi
        if python3 - "$VM_HOST" <<'PYTHON'
import socket
import sys
try:
    with socket.create_connection((sys.argv[1], 22), timeout=2):
        pass
except OSError:
    sys.exit(1)
PYTHON
        then
            # Authenticate once; share the connection for transfer and guest commands.
            ssh "${ssh_options[@]}" "$target" true
            return
        fi
        sleep 2
    done
    echo 'SSH unavailable. Check the VM address and enable sshd in the guest.' >&2
    return 1
}
phase=ssh
wait_for_ssh
phase=upload
# Send the working tree, including uncommitted changes; no Git or push required.
tar --exclude=.git --exclude=.vm-state --exclude=test-results --exclude=__pycache__ --exclude='validation-report*.json' -czf "$work/project.tar.gz" -C "$ROOT" .
remote_dir=$(ssh "${ssh_options[@]}" "$target" 'mkdir -p "$HOME/.local/state/grandma-linux-tests" && mktemp -d "$HOME/.local/state/grandma-linux-tests/run.XXXXXXXX"')
[[ $remote_dir =~ ^/home/[a-zA-Z0-9_-]+/\.local/state/grandma-linux-tests/run\.[a-zA-Z0-9]+$ ]] || exit 1
scp "${ssh_options[@]}" "$work/project.tar.gz" "$target:$remote_dir/project.tar.gz"
if [[ -n ${TEST_PROFILE:-} ]]; then
    [[ -f $TEST_PROFILE ]] || { echo 'TEST_PROFILE not found' >&2; exit 2; }
    scp "${ssh_options[@]}" "$TEST_PROFILE" "$target:$remote_dir/input-profile.yaml"
fi
ssh "${ssh_options[@]}" "$target" "tar -xzf $remote_dir/project.tar.gz -C $remote_dir"
for ((pass=0; pass<3; pass++)); do
    code=0
    phase="guest-setup-$((pass + 1))"
    ssh "${ssh_options[@]}" "$target" "GRANDMA_TEST_UPDATE=$TEST_UPDATE GRANDMA_TEST_PROFILES=$TEST_PROFILES GRANDMA_TEST_CUSTOM_PROFILE=${TEST_PROFILE:+1} python3 $remote_dir/scripts/vm/run-guest.py" || code=$?
    if (( code == 75 )); then
        phase=reboot
        echo 'Rebooting the test VM for the pending deployment...'
        ssh "${ssh_options[@]}" "$target" 'sudo -n systemctl reboot' || { echo 'VM reboot failed.' >&2; exit 1; }
        sleep 5
        wait_for_ssh
        continue
    fi
    phase=collect-results
    for artifact in setup.log execution.json; do
        scp "${ssh_options[@]}" "$target:$remote_dir/$artifact" "${log%.log}-guest-$artifact" || true
    done
    scp "${ssh_options[@]}" "$target:$remote_dir/validation-report.json" "$ROOT/test-results/validation-report.json" || {
        echo 'Setup stopped before validation. See the error above.' >&2; exit 1;
    }
    printf 'Report: %s/test-results/validation-report.json\n' "$ROOT"
    phase=finished
    exit "$code"
done
echo 'Reboot limit reached. Inspect the VM.' >&2
exit 1
