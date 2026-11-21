#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
VM_NAME=${VM_NAME:-fedora-kinoite-test-v2}
VM_USER=${VM_USER:-maria}
URI=${LIBVIRT_URI:-qemu:///system}
action=${1:-}
[[ $VM_NAME =~ ^[a-zA-Z0-9_-]+$ && $VM_USER =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
[[ $action == save || $action == restore || $action == update ]] || { echo 'Usage: baseline.sh save|update|restore' >&2; exit 2; }
for tool in virsh python3 qemu-img; do command -v "$tool" >/dev/null || { echo "Missing: $tool" >&2; exit 1; }; done
if [[ $action == restore ]]; then
    command -v guestfish >/dev/null || { echo 'Missing: guestfish (host libguestfs-tools package)' >&2; exit 1; }
fi
sudo -v
v=(sudo virsh --connect "$URI")
base_dir="/var/lib/libvirt/images/grandma-baselines/$VM_NAME"
base="$base_dir/base.qcow2"
if [[ $action == save ]] && sudo test -e "$base"; then
    echo 'A baseline already exists. Refusing to replace it.' >&2; exit 1
fi
if [[ $action == restore ]]; then
    sudo test -f "$base" || { echo 'No saved baseline.' >&2; exit 1; }
fi
state=$(LC_ALL=C "${v[@]}" domstate "$VM_NAME")
if [[ $state == running ]]; then
    echo 'Requesting a clean VM shutdown...'
    "${v[@]}" shutdown "$VM_NAME"
    for ((attempt=0; attempt<60; attempt++)); do
        state=$(LC_ALL=C "${v[@]}" domstate "$VM_NAME")
        [[ $state != 'shut off' ]] || break
        sleep 2
    done
fi
[[ $state == 'shut off' ]] || { echo 'VM must be fully shut down. Shut it down from KDE and retry.' >&2; exit 1; }
xml=$("${v[@]}" dumpxml "$VM_NAME")
disk=$(python3 -c 'import sys,xml.etree.ElementTree as E
r=E.fromstring(sys.stdin.read())
for d in r.findall("./devices/disk"):
 if d.get("device")=="disk" and d.find("target").get("dev")=="vda":
  print(d.find("source").get("file","")); break' <<< "$xml")
[[ -n $disk ]] && sudo test -f "$disk" || { echo 'Root disk not found.' >&2; exit 1; }
if [[ $action == save || $action == update ]]; then
    sudo install -d -m 0755 "$base_dir"
    echo 'Saving standalone clean baseline...'
    sudo qemu-img convert -p -O qcow2 "$disk" "$base.partial"
    sudo qemu-img check "$base.partial"
    if [[ $action == update ]] && sudo test -f "$base"; then
        sudo cp --reflink=auto --sparse=always -- "$base" "$base_dir/base.previous.qcow2"
    fi
    sudo mv -- "$base.partial" "$base"
    printf '%s\n' "$xml" | sudo tee "$base_dir/domain.xml" >/dev/null
else
    # Check the source before replacing the working disk. Keep ownership/mode.
    sudo qemu-img check "$base"
    echo 'Restoring clean baseline; previous guest test changes will be discarded...'
    sudo cp --reflink=auto --sparse=always -- "$base" "$disk.grandma-restore"
    sudo python3 "$ROOT/scripts/vm/prepare-disk.py" "$disk.grandma-restore" --user "$VM_USER"
    sudo chown --reference="$disk" "$disk.grandma-restore"
    sudo chmod --reference="$disk" "$disk.grandma-restore"
    sudo mv -f -- "$disk.grandma-restore" "$disk"
fi
if command -v restorecon >/dev/null; then sudo restorecon -R "$base_dir" "$disk"; fi
echo "Baseline $action complete."
