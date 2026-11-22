#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install small user tools, a monthly backup timer and localized launchers."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from backup import Backup
from manual import build as build_manual

TOOLS={
 'grandma-help':('Help','Ajuda','help','help-browser'),
 'grandma-guide':('User manual','Manual de uso','guide','help-contents'),
 'grandma-backup':('Backup','Backup','backup','document-save'),
 'grandma-recover':('Recover Files','Recuperar arquivos','recover','document-revert'),
 'grandma-support-info':('Support information','Informações para suporte','info','dialog-information'),
 'grandma-reading':('Reading comfort','Conforto de leitura','reading','preferences-desktop-font'),
 'grandma-updates':('Updates','Atualizações','updates','system-software-update'),
}

def managed(path,content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and '# Grandma Linux managed' not in path.read_text():
        raise RuntimeError('Refusing to replace a personal file: '+str(path))
    path.write_text('# Grandma Linux managed\n'+content)


def update_menu(config):
    path=config/'menus/plasma-applications.menu'
    if not path.is_file():return
    tree=ET.parse(path);root=tree.getroot()
    groups={'Help':['grandma-help','grandma-guide','grandma-support-info'],
            'Utilities':['grandma-backup','grandma-recover'], 'System':['grandma-updates','grandma-reading']}
    for name,ids in groups.items():
        node=next((n for n in root.findall('Menu') if n.findtext('Name')==name),None)
        if node is None:continue
        include=node.find('Include')
        if include is None:include=ET.SubElement(node,'Include')
        existing={n.text for n in include.findall('Filename')}
        for app in ids:
            if app+'.desktop' not in existing:ET.SubElement(include,'Filename').text=app+'.desktop'
    if not path.with_suffix('.menu.before-user-tools').exists():shutil.copyfile(path,path.with_suffix('.menu.before-user-tools'))
    ET.indent(root)
    path.write_text('<?xml version="1.0"?>\n<!-- Grandma Linux managed -->\n'+ET.tostring(root,encoding='unicode'))


def install(root,dry_run=False,update=False):
    if dry_run:
        print('Install User manual, Help, Updates and monthly local backup with safe recovery.');return
    home=Path.home();config=Path(os.environ.get('XDG_CONFIG_HOME',home/'.config'))
    data=Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))
    base=home/'.local/libexec/grandma-linux';base.mkdir(parents=True,exist_ok=True)
    for name in ['backup.py','user-tools.py','project_update.py','reading.py']:
        shutil.copyfile(root/'scripts'/name,base/name)
    shutil.copyfile(root/'VERSION',base/'VERSION')
    # The support launcher is also installed by desktop.py. Copy it here so this
    # module can be installed independently during development.
    shutil.copyfile(root/'scripts/remote-support-session.py',base/'remote-support-session.py')
    (base/'guides').mkdir(exist_ok=True)
    for path in (root/'data/guides').iterdir():
        if path.suffix in {'.txt','.json'}:shutil.copyfile(path,base/'guides'/path.name)
    for app,(en,pt,action,icon) in TOOLS.items():
        command=f'python3 "{base / "user-tools.py"}" {action}' if action else 'plasma-discover --mode update'
        managed(data/'applications'/f'{app}.desktop',f'[Desktop Entry]\nType=Application\nName={en}\nName[pt_BR]={pt}\nExec={command}\nIcon={icon}\nCategories=Utility;\nTerminal=false\n')
    desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
    if not desktop.is_absolute() or desktop==home:raise ValueError('Configure the desktop folder first.')
    desktop.mkdir(parents=True,exist_ok=True)
    language='pt-BR' if os.environ.get('LANG','').startswith('pt_BR') or os.environ.get('LANGUAGE','').startswith('pt_BR') else 'en'
    build_manual(root,desktop/'.grandma-linux-manual.html',language)
    for app in ['grandma-help','grandma-guide']:
        source=data/'applications'/f'{app}.desktop'
        if update and not (desktop/source.name).exists():continue
        managed(desktop/source.name,source.read_text().removeprefix('# Grandma Linux managed\n'))
        (desktop/source.name).chmod(0o755)
    if not update:
        backup=Backup();backup.configure_local()
        unit=config/'systemd/user'
        script=str(base/'user-tools.py').replace('%','%%').replace('"','\\"')
        managed(unit/'grandma-backup.service',f'[Unit]\nDescription=Grandma Linux personal file backup\nConditionPathExists={backup.config_path}\n\n[Service]\nType=oneshot\nExecStart=python3 "{script}" scheduled-backup\nNice=10\nIOSchedulingClass=idle\nUMask=0077\nTimeoutStartSec=infinity\n')
        managed(unit/'grandma-backup.timer','[Unit]\nDescription=Grandma Linux monthly backup\n\n[Timer]\nOnCalendar=monthly\nPersistent=true\nRandomizedDelaySec=30m\n\n[Install]\nWantedBy=timers.target\n')
        if not backup.status_path.exists() or not json.loads(backup.status_path.read_text()).get('last_success'):
            print('Creating the first local file backup...',flush=True);backup.run()
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['systemctl','--user','enable','--now','grandma-backup.timer'],check=True)
    update_menu(config)
    subprocess.run(['update-desktop-database',str(data/'applications')],check=True)
    subprocess.run(['kbuildsycoca6','--noincremental'],check=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true');parser.add_argument('--update',action='store_true');args=parser.parse_args()
    install(Path(__file__).resolve().parent.parent,args.dry_run,args.update)
