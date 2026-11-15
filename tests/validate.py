#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only guest checks. Emits a JSON report and fails when requirements are missing."""
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import shlex
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from desktop import launcher_names

root = Path(__file__).resolve().parent.parent
results = []

def record(name, passed, detail=''):
    results.append({'check': name, 'passed': bool(passed), 'detail': detail})

def command(*args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None

# SSH itself is not a desktop session. Read the active user's imported desktop environment.
manager=command('systemctl','--user','show-environment')
if manager is not None and manager.returncode==0:
    for line in manager.stdout.splitlines():
        if '=' in line:
            key,value=line.split('=',1)
            parts=shlex.split(value)
            os.environ[key]=parts[0] if len(parts)==1 else value
session=command('systemctl','--user','is-active','graphical-session.target')
record('Active desktop session',session is not None and session.returncode==0)
record('Wayland', os.environ.get('XDG_SESSION_TYPE') == 'wayland')
record('KDE', 'KDE' in os.environ.get('XDG_CURRENT_DESKTOP', ''))
record('Brazilian Portuguese session', os.environ.get('LANG', '').startswith('pt_BR'))
for package in ('vim-enhanced', 'restic'):
    result = command('rpm', '-q', package)
    record(package, result is not None and result.returncode == 0)
data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
for row in (root / 'data/apps.tsv').read_text().splitlines():
    if not row or row.startswith('#'):
        continue
    app_id, native, en, pt = row.split('|')
    available = native != '-' and shutil.which(native)
    for scope in ('--user', '--system'):
        result = command('flatpak', 'info', scope, app_id)
        available = available or (result is not None and result.returncode == 0)
    record(app_id, available, 'Availability only; interactive launch still needs testing.')
    candidates = [data / 'applications' / name for name in launcher_names(app_id, native)]
    localized = False
    for candidate in candidates:
        if candidate.is_file():
            parser = configparser.ConfigParser(interpolation=None, strict=False)
            parser.optionxform = str
            parser.read(candidate)
            localized = localized or parser.get('Desktop Entry', 'Name[pt_BR]', fallback='') == pt
    record(f'{app_id}: localized launcher', localized)
result = command('xdg-user-dir', 'DESKTOP')
folder = Path(result.stdout.strip()) if result and result.returncode == 0 else None
for app_id in ('org.kde.dolphin', 'org.kde.gwenview', 'com.brave.Browser', 'org.kde.okular', 'io.missioncenter.MissionCenter','org.onlyoffice.desktopeditors','org.videolan.VLC','org.localsend.localsend_app','org.kde.kwrite'):
    record(f'{app_id}: desktop shortcut', folder is not None and (folder / f'grandma-{app_id}.desktop').is_file())
# Check user-level settings as well as the presence of applications.
for key in ('SingleClick', 'MiddleClickPaste'):
    result=command('kreadconfig6','--file','kdeglobals','--group','KDE','--key',key,'--default','false' if key == 'SingleClick' else 'true')
    record(key, result is not None and result.returncode==0 and result.stdout.strip()=='false')
config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
record('Task menu', (config/'menus/plasma-applications.menu').is_file())
record('Se7en Aero package', (data/'plasma/look-and-feel/Se7enAero/metadata.json').is_file())
result=command('kreadconfig6','--file','plasmarc','--group','Theme','--key','name')
record('Se7en Aero style active', result is not None and result.stdout.strip()=='Se7enAeroStyle')
result=command('kreadconfig6','--file','kdeglobals','--group','KDE','--key','LookAndFeelPackage')
record('Se7en Aero global preset active',result is not None and result.stdout.strip()=='Se7enAero')
result=command('kreadconfig6','--file','kwinrc','--group','org.kde.kdecoration2','--key','theme')
record('Se7en Aero window decoration',result is not None and result.stdout.strip()=='__aurorae__svg__Se7enAero')
from theme import DESTINATIONS
for package in json.loads((root/'data/themes.json').read_text()):
    marker=data/DESTINATIONS[package['id']]/f'.grandma-{package["id"]}.sha256'
    record(f'{package["name"]}: pinned version',marker.is_file() and marker.read_text().strip()==package['sha256'])
for app_id in ('com.brave.Browser','io.missioncenter.MissionCenter'):
    parser=configparser.ConfigParser(interpolation=None,strict=False)
    parser.read(data/'applications'/f'{app_id}.desktop')
    icon=parser.get('Desktop Entry','Icon',fallback='')
    record(f'{app_id}: icon file', bool(icon) and Path(icon).is_absolute() and Path(icon).is_file())
record('WhatsApp shortcut', folder is not None and (folder/'grandma-whatsapp.desktop').is_file())
mime=configparser.ConfigParser(interpolation=None,strict=False)
mime.read(config/'mimeapps.list')
record('Default browser', mime.get('Default Applications','x-scheme-handler/https',fallback='')=='com.brave.Browser.desktop')
record('Default PDF reader', mime.get('Default Applications','application/pdf',fallback='')=='org.kde.okular.desktop')
flameshot=configparser.ConfigParser(interpolation=None,strict=False)
flameshot.read(Path.home()/'.var/app/org.flameshot.Flameshot/config/flameshot/flameshot.ini')
record('Screenshot auto-save', flameshot.get('General','saveAfterCopy',fallback='')=='true')
print(json.dumps({'checks': results, 'manual_checks': ['App launch and rendering', 'Flameshot on Wayland', 'RustDesk connection and shutdown', 'Camera, microphone, audio', 'Backup and restore']}, ensure_ascii=False, indent=2))
sys.exit(0 if all(item['passed'] for item in results) else 1)
