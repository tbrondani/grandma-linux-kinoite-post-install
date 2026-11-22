#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Configure automatic desktop login in the disposable test VM only."""
import argparse
import os
from pathlib import Path
import re
import subprocess


def configure(user, root=Path('/')):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*',user):
        raise ValueError('Invalid VM user')
    session=root/'usr/share/wayland-sessions/plasma.desktop'
    if not session.is_file():raise RuntimeError('Plasma Wayland session not found')
    contents=f'# Grandma Linux test VM only\n[Autologin]\nUser={user}\nSession=plasma.desktop\nRelogin=false\n'
    for relative in ['etc/sddm.conf.d/grandma-test.conf','etc/plasmalogin.conf.d/zz-grandma-test.conf']:
        path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(contents);path.chmod(0o644)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--user',default='tester');args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Run with sudo inside the test VM')
    subprocess.run(['systemd-detect-virt','--vm'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['id','--',args.user],check=True,stdout=subprocess.DEVNULL)
    configure(args.user)
    subprocess.run(['systemctl','enable','--now','sshd'],check=True)
    print('Test VM automatic login configured. It takes effect at the next boot.')
