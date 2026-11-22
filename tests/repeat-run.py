#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Verify that rerunning setup preserves managed files and package inventory."""
import configparser
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess

root=Path(__file__).resolve().parent.parent
env=os.environ.copy()
for line in subprocess.run(['systemctl','--user','show-environment'],check=True,capture_output=True,text=True).stdout.splitlines():
    if '=' in line:
        key,value=line.split('=',1); parts=shlex.split(value)
        env[key]=parts[0] if len(parts)==1 else value

def capture():
    files={}
    for folder in (Path.home()/'.local/share/applications',Path.home()/'.local/share/desktop-directories',Path.home()/'.local/share/plasma/desktoptheme/Se7enAeroStyle'):
        for path in folder.rglob('*'):
            if path.is_file(): files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    desktop=Path(subprocess.run(['xdg-user-dir','DESKTOP'],capture_output=True,text=True,check=True,env=env).stdout.strip())
    for path in desktop.glob('grandma-*.desktop'):
        files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    for filename in ('mimeapps.list','menus/plasma-applications.menu','flameshot/flameshot.ini'):
        path=Path.home()/'.config'/filename
        files[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    inventory=subprocess.run(['flatpak','list','--app','--columns=application,installation'],capture_output=True,text=True,check=True).stdout
    status=json.loads(subprocess.run(['rpm-ostree','status','--json'],capture_output=True,text=True,check=True).stdout)
    config=configparser.ConfigParser(interpolation=None,strict=False)
    config.read(Path.home()/'.config/plasma-org.kde.plasma.desktop-appletsrc')
    wallpaper={section:dict(config[section]) for section in config.sections() if '[Wallpaper]' in section}
    return files,inventory,[d['checksum'] for d in status['deployments']],wallpaper

before=capture()
subprocess.run(['bash',str(root/'setup.sh'),'--lang=pt-BR'],env=env,check=True)
after=capture()
changed=[name for name in before[0].keys()|after[0].keys() if before[0].get(name)!=after[0].get(name)]
result={'passed':before==after,'changed_files':changed,'same_apps':before[1]==after[1],'same_deployments':before[2]==after[2],'same_wallpaper':before[3]==after[3]}
(root/'test-results').mkdir(exist_ok=True)
(root/'test-results/repeat-run.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['passed'] else 1)
