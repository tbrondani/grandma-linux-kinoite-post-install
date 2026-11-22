#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install a pinned reading font and apply reversible, user-selected presets."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
from downloads import open_url

FAMILY='Atkinson Hyperlegible Next'
FONT_KEYS=[('kdeglobals','General',key) for key in ['font','menuFont','toolBarFont','taskbarFont','smallestReadableFont']]+[('kdeglobals','WM','activeFont')]
KEYS=FONT_KEYS+[('kcminputrc','Mouse','cursorSize')]
MISSING='__GRANDMA_MISSING_FONT_SETTING__'


def install(root,dry_run=False):
    if dry_run:
        print('Install Atkinson Hyperlegible Next and its OFL license; keep the current desktop font.');return
    data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
    destination=data/'fonts/grandma-linux/AtkinsonHyperlegibleNext'
    manifest=json.loads((root/'data/reading-fonts.json').read_text())
    # Verify every download before installing any font.
    payloads=[]
    for item in manifest['files']:
        path=destination/item['filename']
        if path.is_file():
            if hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256']:continue
            raise RuntimeError('Refusing to replace a modified font file: '+str(path))
        request=urllib.request.Request(item['url'],headers={'User-Agent':'GrandmaLinux'})
        with open_url(request,timeout=30) as response:
            if not response.url.startswith('https://'):raise RuntimeError('Font download requires HTTPS.')
            payload=response.read(item['size']+1)
        if len(payload)!=item['size'] or hashlib.sha256(payload).hexdigest()!=item['sha256']:
            raise RuntimeError('Reading font checksum mismatch: '+item['filename'])
        payloads.append((path,payload))
    destination.mkdir(parents=True,exist_ok=True)
    for path,payload in payloads:
        temporary=path.with_suffix(path.suffix+'.partial');temporary.write_bytes(payload);temporary.replace(path)
    (destination/'SOURCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
    subprocess.run(['fc-cache','-f',str(destination)],check=True)


def original_path():return Path.home()/'.local/state/grandma-linux/reading-original.json'


def write(file,group,key,value):
    command=['kwriteconfig6','--notify','--file',file,'--group',group,'--key',key]
    command+=['--delete'] if value is None else [str(value)]
    subprocess.run(command,check=True)


def apply(preset):
    if preset not in {'standard','large','restore'}:raise ValueError('Unknown reading preset')
    path=original_path()
    if preset=='restore':
        if not path.is_file():return
        values=json.loads(path.read_text())
        # Restore only the keys we changed, preserving later unrelated settings.
        for file,group,key in KEYS:write(file,group,key,values[file+'|'+group+'|'+key])
        path.unlink();return
    family=subprocess.check_output(['fc-match','--format=%{family}',FAMILY],text=True)
    if FAMILY not in family:raise RuntimeError('Install the reading font before selecting a preset.')
    if not path.is_file():
        values={}
        for file,group,key in KEYS:
            value=subprocess.check_output(['kreadconfig6','--file',file,'--group',group,'--key',key,'--default',MISSING],text=True).rstrip('\n')
            values[file+'|'+group+'|'+key]=None if value==MISSING else value
        path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        temporary=path.with_suffix('.partial');temporary.write_text(json.dumps(values,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
    size=12 if preset=='standard' else 14
    for file,group,key in FONT_KEYS:write(file,group,key,f'{FAMILY},{size},-1,5,50,0,0,0,0,0')
    write('kcminputrc','Mouse','cursorSize','32')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--preset',choices=['standard','large','restore']);args=parser.parse_args()
    if args.preset:
        if args.dry_run:print('Reading preset: '+args.preset)
        else:apply(args.preset)
    else:install(Path(__file__).resolve().parents[1],args.dry_run)
