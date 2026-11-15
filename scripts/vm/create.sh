#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Provision a NEW disposable VM. Never replace an existing domain or disk.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
VM_NAME=${VM_NAME:-fedora-kinoite-test-v2}
VM_USER=${VM_USER:-maria}
URI=${LIBVIRT_URI:-qemu:///system}
FEDORA_VERSION=${FEDORA_VERSION:-45}
[[ $FEDORA_VERSION =~ ^[0-9]+$ ]] || { echo 'Invalid FEDORA_VERSION' >&2; exit 2; }
ISO_PATH=${ISO_PATH:-$ROOT/../Fedora-Kinoite-Installer-45-1.4.x86_64.iso}
[[ -n $ISO_PATH ]] || { echo 'Set ISO_PATH to the Fedora Kinoite 45 installer ISO.' >&2; exit 2; }
export FEDORA_VERSION
[[ $VM_NAME =~ ^[a-zA-Z0-9_-]+$ && $VM_USER =~ ^[a-z_][a-z0-9_-]*$ ]] || exit 2
for tool in virt-install ssh-keygen python3 openssl; do
    command -v "$tool" >/dev/null || { echo "Missing host command: $tool" >&2; exit 1; }
done
[[ -f $ISO_PATH ]] || { printf 'Set ISO_PATH to your Fedora Kinoite installer ISO. Not found: %s\n' "$ISO_PATH" >&2; exit 1; }
virsh_cmd=(virsh --connect "$URI")
if [[ $URI == qemu:///system ]]; then
    sudo -v
    virsh_cmd=(sudo -n virsh --connect "$URI")
fi
if "${virsh_cmd[@]}" dominfo "$VM_NAME" >/dev/null 2>&1; then echo 'VM already exists; not replacing it.' >&2; exit 1; fi
state_dir="$ROOT/.vm-state"
mkdir -p "$state_dir"
chmod 700 "$state_dir"
key="$state_dir/test-key"
if [[ ! -f $key ]]; then ssh-keygen -q -t ed25519 -N '' -C grandma-test-vm -f "$key"; fi
# Ask once for a usable password; store only its hash in the generated Kickstart.
printf 'Choose a login password for %s in the test VM: ' "$VM_USER" > /dev/tty
IFS= read -r -s vm_password < /dev/tty
printf '\n' > /dev/tty
[[ -n $vm_password ]] || { echo 'A non-empty test password is required.' >&2; exit 2; }
VM_PASSWORD_HASH=$(printf '%s' "$vm_password" | openssl passwd -6 -stdin)
unset vm_password
export VM_PASSWORD_HASH
export VM_USER
export VM_PUBLIC_KEY
VM_PUBLIC_KEY=$(cat "$key.pub")
python3 - "$state_dir/ks.cfg" <<'PYTHON'
import os
import subprocess
from pathlib import Path
import sys
version = os.environ['FEDORA_VERSION']
user = os.environ['VM_USER']
key = os.environ['VM_PUBLIC_KEY']
password = os.environ['VM_PASSWORD_HASH']
ks = f'''text
lang pt_BR.UTF-8
keyboard --xlayouts=br
timezone Europe/Lisbon --utc
network --bootproto=dhcp --device=link --activate
rootpw --lock
user --name={user} --groups=wheel --iscrypted --password={password}
sshkey --username={user} "{key}"
firewall --enabled --service=ssh
services --enabled=sshd
selinux --enforcing
ignoredisk --only-use=vda
zerombr
clearpart --all --initlabel --drives=vda
autopart --type=plain
ostreesetup --osname=fedora --remote=fedora --url=file:///ostree/repo --ref=fedora/{version}/x86_64/kinoite --nogpg
reboot
%post --erroronfail
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/grandma-test.conf <<SDDM
[Autologin]
User={user}
Session=plasma.desktop
Relogin=true
SDDM
if [ -f /usr/lib/systemd/system/plasmalogin.service ]; then
    cp /etc/sddm.conf.d/grandma-test.conf /etc/plasmalogin.conf
fi
systemctl enable sshd
# Disposable VM only: allow the test runner to install layered packages and reboot.
echo '{user} ALL=(root) NOPASSWD: /usr/bin/rpm-ostree, /usr/bin/systemctl reboot' > /etc/sudoers.d/grandma-test
chmod 440 /etc/sudoers.d/grandma-test
systemctl set-default graphical.target
%end
'''
Path(sys.argv[1]).write_text(ks)
PYTHON
# Libvirt's qemu user must not depend on access to the host user's home.
media_dir=/var/lib/libvirt/images/grandma-media
media_path="$media_dir/Fedora-Kinoite-${FEDORA_VERSION}-installer.iso"
sudo install -d -m 0755 "$media_dir"
if ! sudo test -f "$media_path" || ! sudo cmp -s -- "$ISO_PATH" "$media_path"; then
    echo 'Copying installer ISO to libvirt storage...'
    sudo install -m 0644 -- "$ISO_PATH" "$media_path"
fi
if command -v restorecon >/dev/null; then sudo restorecon -R "$media_dir"; fi
ISO_PATH=$media_path
sudo virt-install --connect "$URI" --name "$VM_NAME" --memory 8192 --vcpus 4 \
    --cpu host-passthrough --disk size=40,format=qcow2,bus=virtio \
    --location "$ISO_PATH,kernel=images/pxeboot/vmlinuz,initrd=images/pxeboot/initrd.img" --initrd-inject "$state_dir/ks.cfg" \
    --extra-args "inst.ks=file:/ks.cfg inst.stage2=hd:LABEL=Fedora-${FEDORA_VERSION}-Kinoite-x86_64" --os-variant fedora-unknown \
    --network network=default,model=virtio --graphics spice,listen=none \
    --video virtio --boot uefi --noautoconsole
