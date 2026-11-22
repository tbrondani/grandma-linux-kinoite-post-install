#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render new test-VM provisioning without touching an existing domain."""
import os
from pathlib import Path
import re
import sys


def render(user,password,key,version='45',autologin=True,locale='pt_BR.UTF-8'):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',user) or not re.fullmatch(r'[0-9]+',version):raise ValueError('Invalid VM user or Fedora version')
    if locale not in {'pt_BR.UTF-8','en_US.UTF-8'}:raise ValueError('Unsupported VM locale')
    if any(c in password+key for c in '\n\r"'):raise ValueError('Invalid password hash or SSH key')
    keyboard='br' if locale.startswith('pt_') else 'us'
    login=f'''mkdir -p /etc/sddm.conf.d /etc/plasmalogin.conf.d
cat > /etc/sddm.conf.d/grandma-test.conf <<SDDM
[Autologin]
User={user}
Session=plasma.desktop
Relogin=false
SDDM
if [ -f /usr/lib/systemd/system/plasmalogin.service ]; then
    cp /etc/sddm.conf.d/grandma-test.conf /etc/plasmalogin.conf.d/zz-grandma-test.conf
fi
''' if autologin else ''
    return f'''text
lang {locale}
keyboard --xlayouts={keyboard}
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
{login}systemctl enable sshd
# Disposable VM only: allow the test runner to install layered packages and reboot.
echo '{user} ALL=(root) NOPASSWD: /usr/bin/rpm-ostree, /usr/bin/systemctl reboot' > /etc/sudoers.d/grandma-test
chmod 440 /etc/sudoers.d/grandma-test
systemctl set-default graphical.target
%end
'''

if __name__=='__main__':
    Path(sys.argv[1]).write_text(render(os.environ['VM_USER'],os.environ['VM_PASSWORD_HASH'],os.environ['VM_PUBLIC_KEY'],os.environ['FEDORA_VERSION'],os.environ['VM_AUTOLOGIN']=='1',os.environ['VM_LOCALE']))
