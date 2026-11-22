#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare auto-login in an OFFLINE working copy of the plain-layout test disk."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile


def prepare(image,user):
    if not re.fullmatch(r'[a-z_][a-z0-9_-]*',user):raise ValueError('Invalid VM user')
    if not image.is_file() or not image.name.endswith('.grandma-restore'):
        raise ValueError('Use an offline .grandma-restore working copy, never the baseline or live disk')
    args=['guestfish','--ro','-a',str(image),'-m','/dev/sda3']
    listing=subprocess.check_output(args+['ls','/ostree/deploy/fedora/deploy'],text=True)
    deployments=[name for name in listing.splitlines() if re.fullmatch(r'[a-f0-9]{64}\.\d+',name)]
    if not deployments:raise RuntimeError('No Fedora OSTree deployment found; disk was not changed')
    content=f'# Grandma Linux test VM only\n[Autologin]\nUser={user}\nSession=plasma.desktop\nRelogin=false\n'
    quote=json.dumps
    commands=[]
    with tempfile.TemporaryDirectory(prefix='grandma-vm-login-') as folder:
        source=Path(folder)/'login.conf';source.write_text(content)
        for deployment in deployments:
            etc='/ostree/deploy/fedora/deploy/'+deployment+'/etc/'
            for relative in ['sddm.conf.d/grandma-test.conf','plasmalogin.conf.d/zz-grandma-test.conf']:
                target=etc+relative;directory=str(Path(target).parent)
                commands.extend(['mkdir-p '+quote(directory),'upload '+quote(str(source))+' '+quote(target),'chmod 0644 '+quote(target)])
                # Fedora configuration paths use etc_t. Preserve readable SELinux
                # labels when creating files through the offline appliance.
                for path in [directory,target]:
                    label='system_u:object_r:etc_t:s0'
                    commands.append(f'setxattr security.selinux {quote(label)} {len(label)} {quote(path)}')
        subprocess.run(['guestfish','--rw','-a',str(image),'-m','/dev/sda3'],input='\n'.join(commands)+'\n',text=True,check=True)
    print(f'Automatic login prepared for {user} in {len(deployments)} offline deployments.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image',type=Path);parser.add_argument('--user',default='tester');args=parser.parse_args()
    prepare(args.image,args.user)
