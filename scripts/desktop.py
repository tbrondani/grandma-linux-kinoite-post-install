#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create localized launchers from installed desktop entries, preserving Exec."""
import argparse
import configparser
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import urllib.request


def entries(root):
    for row in (root / 'data/apps.tsv').read_text().splitlines():
        if row and not row.startswith('#'):
            yield row.split('|')


DESKTOP_ALIASES = {'org.kde.kdeconnect': 'org.kde.kdeconnect.app.desktop'}


def launcher_names(app_id, native):
    names = [DESKTOP_ALIASES.get(app_id, f'{app_id}.desktop')]
    if f'{app_id}.desktop' not in names:
        names.append(f'{app_id}.desktop')
    if native != '-':
        names.append(f'{native}.desktop')
    return names


def resolve_icon(icon, search):
    if not icon or Path(icon).is_absolute():
        return icon
    # A desktop session started before Flatpak installation may not include its
    # export paths in XDG_DATA_DIRS. Absolute exported icon paths work immediately.
    for folder in search:
        if 'flatpak' not in str(folder):
            continue
        icons = folder.parent / 'icons' / 'hicolor'
        for size in ('scalable', '256x256', '128x128', '64x64', '48x48'):
            for extension in ('.svg', '.png', '.svgz'):
                candidate = icons / size / 'apps' / f'{icon}{extension}'
                if candidate.is_file():
                    return str(candidate.absolute())
    return icon


def browser_icon(root, data):
    metadata = json.loads((root / 'data/internet-icon.json').read_text())
    target = data / 'icons/hicolor/256x256/apps/grandma-internet.png'
    if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != metadata['sha256']:
        with urllib.request.urlopen(metadata['url'], timeout=30) as response:
            payload = response.read(1024 * 1024)
        if hashlib.sha256(payload).hexdigest() != metadata['sha256']:
            raise RuntimeError('Chromium icon checksum mismatch.')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return str(target)


def desktop_dir():
    result = subprocess.run(['xdg-user-dir', 'DESKTOP'], check=True, capture_output=True, text=True)
    path = Path(result.stdout.strip())
    if not path.is_absolute() or path == Path.home():
        raise RuntimeError('Configure an explicit desktop folder with xdg-user-dirs first.')
    return path


def configure(root, dry_run=False):
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    search = [data / 'applications', Path.home() / '.local/share/flatpak/exports/share/applications',
              Path('/var/lib/flatpak/exports/share/applications'), Path('/usr/share/applications')]
    destination = data / 'applications'
    desktop = None if dry_run else desktop_dir()
    shortcuts = {'org.kde.dolphin', 'org.kde.gwenview', 'com.brave.Browser', 'org.kde.okular', 'io.missioncenter.MissionCenter', 'org.onlyoffice.desktopeditors', 'org.videolan.VLC', 'org.localsend.localsend_app', 'org.kde.kwrite'}
    for app_id, native, english, portuguese in entries(root):
        if dry_run:
            print(f'Launcher: {english} / {portuguese}')
            continue
        candidates = [folder / name for folder in search for name in launcher_names(app_id, native)]
        source = next((p for p in candidates if p.is_file()), None)
        if source is None:
            raise RuntimeError(f'No installed desktop entry for {app_id}')
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read(source)
        entry = parser['Desktop Entry']
        if not entry.get('Exec'):
            raise RuntimeError(f'No Exec in {source}')
        entry['Icon'] = browser_icon(root, data) if app_id == 'com.brave.Browser' else resolve_icon(entry.get('Icon', ''), search)
        entry['Name'] = english
        entry['Name[en_US]'] = english
        entry['Name[pt_BR]'] = portuguese
        entry['Keywords'] = f'{english};{native};'
        entry['Keywords[pt_BR]'] = f'{portuguese};{native};'
        entry.pop('Hidden', None)
        entry.pop('NoDisplay', None)
        destination.mkdir(parents=True, exist_ok=True)
        # Same basename overrides the original menu entry instead of duplicating it.
        target = destination / source.name
        if target.exists() and '# Grandma Linux managed' not in target.read_text():
            backup = target.with_suffix('.desktop.before-grandma')
            if not backup.exists():
                shutil.copy2(target, backup)
        with target.open('w') as stream:
            stream.write('# Grandma Linux managed\n')
            parser.write(stream, space_around_delimiters=False)
        if app_id in shortcuts:
            desktop.mkdir(parents=True, exist_ok=True)
            shortcut = desktop / f'grandma-{app_id}.desktop'
            if shortcut.exists() and '# Grandma Linux managed' not in shortcut.read_text():
                raise RuntimeError(f'Refusing to overwrite personal shortcut: {shortcut}')
            shutil.copyfile(target, shortcut)
            shortcut.chmod(0o755)
    if not dry_run:
        # A web-app launcher reuses the installed browser invocation (including Flatpak flags).
        browser = destination / 'com.brave.Browser.desktop'
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        parser.read(browser)
        entry = parser['Desktop Entry']
        entry['Name'] = 'WhatsApp'
        entry['Name[pt_BR]'] = 'WhatsApp'
        entry['Name[en_US]'] = 'WhatsApp'
        entry['Exec'] = entry['Exec'].replace('%U', '--app=https://web.whatsapp.com/').replace('%u', '--app=https://web.whatsapp.com/')
        icon = data / 'icons/hicolor/scalable/apps/grandma-chat.svg'
        icon.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / 'assets/chat.svg', icon)
        entry['Icon'] = str(icon)
        entry.pop('Actions', None)
        for section in list(parser.sections()):
            if section != 'Desktop Entry':
                parser.remove_section(section)
        webapp = destination / 'grandma-whatsapp.desktop'
        with webapp.open('w') as stream:
            stream.write('# Grandma Linux managed\n')
            parser.write(stream, space_around_delimiters=False)
        shutil.copyfile(webapp, desktop / webapp.name)
        (desktop / webapp.name).chmod(0o755)
        subprocess.run(['update-desktop-database', str(destination)], check=True)


if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--dry-run', action='store_true')
    configure(Path(__file__).resolve().parent.parent, args.parse_args().dry_run)
