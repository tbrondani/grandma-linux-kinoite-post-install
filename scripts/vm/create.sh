#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Provision a NEW disposable VM. Never replace an existing domain or disk.
set -Eeuo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
VM_NAME=${VM_NAME:-fedora-kinoite-test-v2}
if [[ ${1:-} == --config ]]; then
    [[ $# == 2 ]] || { echo 'Usage: create.sh [--config profile.yaml]' >&2; exit 2; }
    VM_CONFIG=$2
fi
if [[ -n ${VM_CONFIG:-} ]]; then
    vm_values=$(python3 "$ROOT/scripts/vm/profile.py" "$VM_CONFIG")
    mapfile -t vm_values <<< "$vm_values"
    [[ ${#vm_values[@]} == 3 ]] || exit 2
    VM_USER=${vm_values[0]}
    VM_AUTOLOGIN=${vm_values[1]}
    VM_LOCALE=${vm_values[2]}
fi
export VM_AUTOLOGIN=${VM_AUTOLOGIN:-1}
export VM_LOCALE=${VM_LOCALE:-pt_BR.UTF-8}
VM_USER=${VM_USER:-tester}
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
if (( EUID != 0 )); then
    exec sudo -- /usr/bin/env VM_NAME="$VM_NAME" VM_USER="$VM_USER" LIBVIRT_URI="$URI" VM_AUTOLOGIN="$VM_AUTOLOGIN" VM_LOCALE="$VM_LOCALE" FEDORA_VERSION="$FEDORA_VERSION" ISO_PATH="$ISO_PATH" /bin/bash "$ROOT/scripts/vm/create.sh"
fi
virsh_cmd=(virsh --connect "$URI")
if "${virsh_cmd[@]}" dominfo "$VM_NAME" >/dev/null 2>&1; then echo 'VM already exists; not replacing it.' >&2; exit 1; fi
state_dir="$ROOT/.vm-state"
restore_key_owner() {
    if [[ ${SUDO_UID:-0} =~ ^[0-9]+$ && ${SUDO_GID:-0} =~ ^[0-9]+$ ]] && (( ${SUDO_UID:-0} != 0 )); then
        for path in "$state_dir" "$state_dir/test-key" "$state_dir/test-key.pub" "$state_dir/ks.cfg"; do
            if [[ -e $path && ! -L $path ]]; then chown "$SUDO_UID:$SUDO_GID" "$path"; fi
        done
    fi
}
trap restore_key_owner EXIT
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
python3 "$ROOT/scripts/vm/kickstart.py" "$state_dir/ks.cfg"
# Libvirt's qemu user must not depend on access to the host user's home.
media_dir=/var/lib/libvirt/images/grandma-media
media_path="$media_dir/Fedora-Kinoite-${FEDORA_VERSION}-installer.iso"
install -d -m 0755 "$media_dir"
if ! test -f "$media_path" || ! cmp -s -- "$ISO_PATH" "$media_path"; then
    echo 'Copying installer ISO to libvirt storage...'
    install -m 0644 -- "$ISO_PATH" "$media_path"
fi
if command -v restorecon >/dev/null; then restorecon -R "$media_dir"; fi
ISO_PATH=$media_path
virt-install --connect "$URI" --name "$VM_NAME" --memory 8192 --vcpus 4 \
    --cpu host-passthrough --disk size=40,format=qcow2,bus=virtio \
    --location "$ISO_PATH,kernel=images/pxeboot/vmlinuz,initrd=images/pxeboot/initrd.img" --initrd-inject "$state_dir/ks.cfg" \
    --extra-args "inst.ks=file:/ks.cfg inst.stage2=hd:LABEL=Fedora-${FEDORA_VERSION}-Kinoite-x86_64" --os-variant fedora-unknown \
    --network network=default,model=virtio --graphics spice,listen=none \
    --video virtio --boot uefi --noautoconsole
