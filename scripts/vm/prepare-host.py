#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""One privileged host preparation phase; guest installation stays unprivileged."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]


def virsh(uri,*args):
    return subprocess.check_output(['virsh','--connect',uri,*args],text=True,env=dict(os.environ,LC_ALL='C')).strip()


def prepare(args):
    env=dict(os.environ,VM_NAME=args.vm,VM_USER=args.user,LIBVIRT_URI=args.uri,VM_AUTOLOGIN='1' if args.autologin else '0',VM_LOCALE=args.locale,FEDORA_VERSION=args.fedora)
    if args.iso:env['ISO_PATH']=args.iso
    if subprocess.run(['virsh','--connect',args.uri,'dominfo',args.vm],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        subprocess.run(['bash',str(ROOT/'scripts/vm/create.sh')],env=env,check=True)
    base=Path('/var/lib/libvirt/images/grandma-baselines')/args.vm/'base.qcow2'
    if args.fresh and base.is_file():
        subprocess.run(['bash',str(ROOT/'scripts/vm/baseline.sh'),'restore'],env=env,check=True)
    xml=ET.fromstring(virsh(args.uri,'dumpxml',args.vm))
    networks=sorted({node.find('source').get('network') for node in xml.findall('./devices/interface') if node.get('type')=='network' and node.find('source') is not None})
    for name in networks:
        if not name:continue
        info=virsh(args.uri,'net-info',name)
        active=next((line.split(':',1)[1].strip() for line in info.splitlines() if line.startswith('Active:')),'no')
        if active!='yes':subprocess.run(['virsh','--connect',args.uri,'net-start',name],check=True)
    state=virsh(args.uri,'domstate',args.vm)
    if state=='shut off':subprocess.run(['virsh','--connect',args.uri,'start',args.vm],check=True)
    elif state!='running':raise RuntimeError('VM state requires attention: '+state)
    host=args.host
    for attempt in range(60):
        if host:break
        if attempt%10==0:print('Waiting for DHCP ('+str(attempt*2)+' seconds)...',flush=True)
        addresses=virsh(args.uri,'domifaddr',args.vm,'--source','lease')
        host=next((line.split()[3].split('/')[0] for line in addresses.splitlines() if len(line.split())>=4 and line.split()[2]=='ipv4'),'')
        if not host:time.sleep(2)
    if not host or not re.fullmatch(r'[a-zA-Z0-9.:_-]+',host):raise RuntimeError('Cannot discover VM address. Set VM_HOST explicitly.')
    display=subprocess.run(['virsh','--connect',args.uri,'domdisplay',args.vm],capture_output=True,text=True)
    return dict(host=host,display=display.stdout.strip() if display.returncode==0 else '',vm=args.vm)


def write_report(path,result):
    # The calling user creates the private report file. Never follow a symlink
    # or overwrite a file owned by a different account through this helper.
    descriptor=os.open(path,os.O_WRONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'w') as output:
        info=os.fstat(output.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=int(os.environ.get('SUDO_UID',os.getuid())):raise RuntimeError('Invalid host report owner')
        os.ftruncate(output.fileno(),0)
        json.dump(result,output)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vm',required=True);parser.add_argument('--user',required=True)
    parser.add_argument('--uri',default='qemu:///system');parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--fresh',action='store_true');parser.add_argument('--host',default='')
    parser.add_argument('--iso');parser.add_argument('--fedora',default='45')
    parser.add_argument('--locale',default='pt_BR.UTF-8');parser.add_argument('--no-autologin',dest='autologin',action='store_false')
    args=parser.parse_args()
    if os.geteuid()!=0:parser.error('Run through start-test.sh; this phase requires the single host authorization.')
    if args.uri!='qemu:///system' or not re.fullmatch(r'[A-Za-z0-9_-]+',args.vm) or not re.fullmatch(r'[a-z_][a-z0-9_-]*',args.user):parser.error('Invalid VM parameters')
    if not re.fullmatch(r'[0-9]+',args.fedora) or args.locale not in {'en_US.UTF-8','pt_BR.UTF-8'}:parser.error('Invalid provisioning preferences')
    write_report(args.report,prepare(args))

if __name__=='__main__':main()
