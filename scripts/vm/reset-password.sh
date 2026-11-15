#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Host-side repair for the plain ext4 Kinoite test VM created by create.sh.
set -Eeuo pipefail
VM_NAME=${VM_NAME:-fedora-kinoite-test-v2}
[[ $VM_NAME =~ ^[a-zA-Z0-9_-]+$ ]] || exit 2
for tool in guestfish openssl python3 virsh; do
    command -v "$tool" >/dev/null || { echo "Missing: $tool. Install host packages: sudo dnf install libguestfs-tools-c guestfs-tools" >&2; exit 1; }
done
sudo -v
state=$(sudo env LC_ALL=C virsh --connect qemu:///system domstate "$VM_NAME")
[[ $state == 'shut off' ]] || { echo 'Shut down the VM before changing its disk.' >&2; exit 1; }
work=$(mktemp -d)
chmod 700 "$work"
trap 'sudo rm -rf -- "$work"' EXIT
sudo virsh --connect qemu:///system dumpxml "$VM_NAME" > "$work/domain.xml"
disk=$(python3 - "$work/domain.xml" <<'PYTHON'
import sys
import xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot()
for disk in root.findall('./devices/disk'):
    if disk.get('device') == 'disk' and disk.find('target').get('dev') == 'vda':
        print(disk.find('source').get('file', ''))
        break
PYTHON
)
[[ -n $disk && -f $disk ]] || { echo 'Cannot locate the VM root disk.' >&2; exit 1; }
# Atomic desktops store mutable /etc inside the deployment, not a conventional root.
shadow_paths=$(sudo guestfish --ro -a "$disk" run : mount-ro /dev/sda3 / : glob-expand '/ostree/deploy/fedora/deploy/*/etc/shadow')
[[ -n $shadow_paths ]] || { echo 'No Kinoite deployment found. Disk was not modified.' >&2; exit 1; }
printf 'Nova senha para maria: '
IFS= read -r -s password
printf '\n'
[[ -n $password ]] || { echo 'Empty password refused.' >&2; exit 2; }
printf 'Repita a senha: '
IFS= read -r -s confirmation
printf '\n'
[[ $password == "$confirmation" ]] || { echo 'Passwords do not match.' >&2; exit 2; }
printf '%s' "$password" | openssl passwd -6 -stdin > "$work/hash"
unset password confirmation
while IFS= read -r shadow; do
    [[ $shadow =~ ^/ostree/deploy/fedora/deploy/[a-zA-Z0-9.]+/etc/shadow$ ]] || { echo 'Unexpected deployment path.' >&2; exit 1; }
    sudo guestfish --ro -a "$disk" run : mount-ro /dev/sda3 / : download "$shadow" "$work/shadow"
    sudo python3 - "$work/shadow" "$work/hash" <<'PYTHON'
from pathlib import Path
import sys
p=Path(sys.argv[1]); hashed=Path(sys.argv[2]).read_text().strip()
rows=p.read_text().splitlines(); found=False
for i,row in enumerate(rows):
    fields=row.split(':')
    if fields[0]=='maria':
        fields[1]=hashed
        rows[i]=':'.join(fields); found=True
if not found: sys.exit('User maria not found; refusing to modify shadow.')
p.write_text('\n'.join(rows)+'\n')
PYTHON
    sudo guestfish --rw -a "$disk" run : mount /dev/sda3 / : upload "$work/shadow" "$shadow"
done <<< "$shadow_paths"
echo 'Senha de maria redefinida. Iniciando a VM...'
sudo virsh --connect qemu:///system start "$VM_NAME"
