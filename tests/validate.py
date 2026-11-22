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
import sqlite3
import tomllib
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from desktop import launcher_names
from profiles import load,selected,feature

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
for package in ('vim-enhanced', 'restic', 'python3-dbus', 'python3-gobject-base'):
    if package=='restic' and not feature('backup'):continue
    result = command('rpm', '-q', package)
    record(package, result is not None and result.returncode == 0)
data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
chosen=selected(root,load(root));chosen_ids={row[0] for row in chosen}
for app_id,native,en,pt in chosen:
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
    if app_id not in chosen_ids:continue
    record(f'{app_id}: desktop shortcut', folder is not None and (folder / f'grandma-{app_id}.desktop').is_file())
# Check user-level settings as well as the presence of applications.
for key in ('SingleClick', 'MiddleClickPaste'):
    result=command('kreadconfig6','--file','kdeglobals','--group','KDE','--key',key,'--default','false' if key == 'SingleClick' else 'true')
    record(key, result is not None and result.returncode==0 and result.stdout.strip()=='false')
config=Path(os.environ.get('XDG_CONFIG_HOME',str(Path.home()/'.config')))
record('Task menu', (config/'menus/plasma-applications.menu').is_file())
if feature('theme'):
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
    if app_id not in chosen_ids:continue
    parser=configparser.ConfigParser(interpolation=None,strict=False)
    parser.read(data/'applications'/f'{app_id}.desktop')
    icon=parser.get('Desktop Entry','Icon',fallback='')
    record(f'{app_id}: icon file', bool(icon) and Path(icon).is_absolute() and Path(icon).is_file())
if feature('theme'):
    result=command('kreadconfig6','--file','kdeglobals','--group','Icons','--key','Theme')
    record('Windows 7 icons active',result is not None and result.stdout.strip()=='Windows-7-1.0')
if feature('accessibility'):
    font_manifest=json.loads((root/'data/reading-fonts.json').read_text())
    import hashlib
    for item in font_manifest['files']:
        path=data/'fonts/grandma-linux/AtkinsonHyperlegibleNext'/item['filename']
        record('Reading font: '+item['filename'],path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==item['sha256'])
    record('Reading comfort launcher',(data/'applications/grandma-reading.desktop').is_file())
record('WhatsApp shortcut', folder is not None and (folder/'grandma-whatsapp.desktop').is_file())
mime=configparser.ConfigParser(interpolation=None,strict=False)
mime.read(config/'mimeapps.list')
record('Default browser', mime.get('Default Applications','x-scheme-handler/https',fallback='')=='com.brave.Browser.desktop')
if 'org.kde.okular' in chosen_ids:record('Default PDF reader', mime.get('Default Applications','application/pdf',fallback='')=='org.kde.okular.desktop')
if 'org.flameshot.Flameshot' in chosen_ids:
    flameshot=configparser.ConfigParser(interpolation=None,strict=False)
    flameshot.read(Path.home()/'.var/app/org.flameshot.Flameshot/config/flameshot/flameshot.ini')
    record('Screenshot auto-save', flameshot.get('General','saveAfterCopy',fallback='')=='true')
if feature('dictionaries'):
    dictionaries=Path.home()/'.var/app/com.ktechpit.omnidict/data/ktechpit/omnidict/dictionaries'
    for package in json.loads((root/'data/dictionaries.json').read_text()):
        path=dictionaries/package['dict_id']/package['version']/'dict.sqlite'
        valid=False
        if path.is_file():
            try:
                with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as database:
                    metadata=dict(database.execute('select key,value from meta'))
                    valid=metadata.get('dict_id')==package['dict_id'] and int(metadata.get('entry_count',0))>0
            except sqlite3.Error:
                pass
        record(f'{package["dict_id"]}: offline data',valid)
if feature('offline_maps'):
    # Validate actual map bytes against the catalogue packaged with the installed app.
    import importlib.util
    map_spec=importlib.util.spec_from_file_location('grandma_maps',root/'scripts/maps.py')
    map_module=importlib.util.module_from_spec(map_spec)
    map_spec.loader.exec_module(map_module)
    try:
        catalogue=map_module.read_catalogue()
        regions=json.loads((root/'data/offline-regions.json').read_text())['download_regions']
        map_root=map_module.map_directory(catalogue)/str(catalogue['v'])
        for leaf in map_module.select(catalogue,regions):
            record(f'{leaf["id"]}: offline map integrity',map_module.valid(map_root/f'{leaf["id"]}.mwm',leaf))
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:
        record('Offline map catalogue',False,str(error))
if os.environ.get('GRANDMA_TEST_VM')=='1':
    login=configparser.ConfigParser(interpolation=None,strict=False)
    login.read('/etc/plasmalogin.conf.d/zz-grandma-test.conf')
    record('Test VM: Test user automatic login',login.get('Autologin','User',fallback='')=='tester')
    record('Test VM: Wayland login session',login.get('Autologin','Session',fallback='')=='plasma.desktop')
    ssh=command('systemctl','is-enabled','sshd')
    record('Test VM: system SSH enabled',ssh is not None and ssh.stdout.strip()=='enabled')
record('Fastfetch installed', shutil.which('fastfetch') is not None)
if feature('translator'):
    translator=Path.home()/'.local/share/grandma-linux/translator'
    record('Translator: isolated Python', (translator/'venv/bin/python').is_file())
    record('Translator: menu launcher', (Path.home()/'.local/share/applications/grandma-translator.desktop').is_file())
    model_root=Path.home()/'.local/share/argos-translate/packages'
    models=[json.loads(p.read_text()) for p in model_root.glob('*/metadata.json')]
    for expected in json.loads((root/'data/translation-models.json').read_text()):
        record('Translator: '+expected['code'],any(all(p.get(k)==expected[k] for k in ['from_code','to_code','package_version']) for p in models))
menu_path=config/'menus/plasma-applications.menu'
menu_text=menu_path.read_text() if menu_path.is_file() else ''
for app in ['grandma-help','grandma-guide','grandma-backup','grandma-recover','grandma-support-info','grandma-updates']:
    if app in {'grandma-backup','grandma-recover'} and not feature('backup'):continue
    path=Path.home()/'.local/share/applications'/f'{app}.desktop'
    record(app+': launcher',path.is_file())
    record(app+': task menu',path.name in menu_text)
for language in ['en','pt-BR']:
    manual_path=Path.home()/'.local/libexec/grandma-linux/guides'/f'manual.{language}.json'
    record('User manual: '+language,manual_path.is_file())
    if manual_path.is_file():
        record('User manual topics: '+language,len(json.loads(manual_path.read_text()).get('topics',[]))==16)
desktop_folder=command('xdg-user-dir','DESKTOP')
manual_html=Path(desktop_folder.stdout.strip())/'.grandma-linux-manual.html' if desktop_folder is not None else None
record('User manual: standalone HTML',manual_html is not None and manual_html.is_file() and 'manual-data' in manual_html.read_text())
if feature('backup'):
    from backup import Backup
    local_backup=Backup()
    record('Local backup: configured',local_backup.config_path.is_file())
    try:
        local_backup.validate(local_backup.config())
        record('Local backup: recovery key permissions', (Path(local_backup.config()['root'])/'recovery-key.txt').stat().st_mode&0o777==0o600)
        record('Local backup: snapshot exists',len(local_backup.snapshots())>0)
        record('Local backup: first copy successful',bool(json.loads(local_backup.status_path.read_text()).get('last_success')))
    except (OSError,ValueError,RuntimeError):record('Local backup: accessible',False)
    timer=command('systemctl','--user','is-enabled','grandma-backup.timer')
    record('Local backup: timer enabled',timer is not None and timer.stdout.strip()=='enabled')
    timer=command('systemctl','--user','is-active','grandma-backup.timer')
    record('Local backup: timer active',timer is not None and timer.stdout.strip()=='active')
if feature('remote_support'):
    remote=Path.home()/'.var/app/com.rustdesk.RustDesk/config/rustdesk/RustDesk2.toml'
    options=tomllib.loads(remote.read_text()).get('options',{}) if remote.is_file() else {}
    record('Remote support: temporary password only',options.get('verification-method')=='use-temporary-password')
    record('Remote support: direct IP disabled',options.get('direct-server')=='N')
if feature('accessibility'):
    night=command('kreadconfig6','--file','kwinrc','--group','NightColor','--key','Active','--default','false')
    record('Night light enabled',night is not None and night.stdout.strip()=='true')
    if (config/'knighttimerc').is_file():
        for key,value in [('SunsetStart','19:00:00'),('SunriseStart','05:00:00')]:
            result=command('kreadconfig6','--file','knighttimerc','--group','Times','--key',key)
            record(f'Night light: {key}',result is not None and result.stdout.strip()==value)
from profiles import manifest_path,profile_path
record('Installer command',(Path.home()/'.local/bin/grandma-install').is_file())
record('Profile preferences saved',profile_path().is_file())
try:
    applied=json.loads(manifest_path().read_text())
    record('Profile applied state',applied.get('profile')==load(root))
    snapshot=Path.home()/'.local/state/grandma-linux/profile-snapshots'/str(applied.get('profile_snapshot',''))
    snapshot=snapshot.with_suffix('.json')
    record('Profile history complete',snapshot.is_file() and json.loads(snapshot.read_text()).get('status')=='complete')
except (OSError,ValueError):record('Profile applied state',False)
print(json.dumps({'checks': results, 'manual_checks': ['App launch and rendering', 'Flameshot on Wayland', 'RustDesk connection and shutdown', 'Camera, microphone, audio', 'Backup and restore', 'Portugal offline rendering, routing and search; choose Brazilian states']}, ensure_ascii=False, indent=2))
sys.exit(0 if all(item['passed'] for item in results) else 1)
