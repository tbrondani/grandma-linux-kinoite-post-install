#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install reviewed Se7en Aero packages directly from KDE Store with SHA-256 pins."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

DESTINATIONS = {1407086: 'plasma/look-and-feel/Se7enAero',1406638:'aurorae/themes',
                2143603:'color-schemes',1407084:'plasma/desktoptheme/Se7enAeroStyle',1407137:'icons'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(package, cache):
    target=cache/f'{package["id"]}-{package["sha256"]}.archive'
    if target.is_file() and digest(target)==package['sha256']:
        return target
    api=f'https://api.kde-look.org/ocs/v1/content/data/{package["id"]}'
    with urllib.request.urlopen(api,timeout=30) as response:
        content=ET.fromstring(response.read()).find('.//content')
    if content is None:
        raise RuntimeError(f'KDE Store did not return package {package["id"]}')
    url=None
    for field in content:
        if field.tag.startswith('downloadname') and field.text==package['filename']:
            url=content.findtext('downloadlink'+field.tag[len('downloadname'):])
            break
    if not url or not url.startswith('https://'):
        raise RuntimeError(f'Pinned download unavailable: {package["name"]}')
    with urllib.request.urlopen(url,timeout=90) as response:
        if not response.url.startswith('https://'):
            raise RuntimeError('Non-HTTPS theme download refused.')
        payload=response.read(40*1024*1024+1)
    if len(payload)>40*1024*1024 or hashlib.sha256(payload).hexdigest()!=package['sha256']:
        raise RuntimeError(f'Theme checksum mismatch: {package["name"]}; review upstream before updating the pin.')
    cache.mkdir(parents=True,exist_ok=True)
    temporary=target.with_suffix('.partial')
    temporary.write_bytes(payload)
    temporary.replace(target)
    return target


def install(root, data):
    packages=json.loads((root/'data/themes.json').read_text())
    cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'grandma-linux/themes'
    archives=[(p,fetch(p,cache)) for p in packages]
    for package,archive in archives:
        destination=data/DESTINATIONS[package['id']]
        marker=destination/f'.grandma-{package["id"]}.sha256'
        if marker.is_file() and marker.read_text().strip()==package['sha256']:
            continue
        with tempfile.TemporaryDirectory() as folder:
            staging=Path(folder)
            if zipfile.is_zipfile(archive):
                with zipfile.ZipFile(archive) as source:
                    for entry in source.infolist():
                        path=(staging/entry.filename).resolve()
                        if not path.is_relative_to(staging):
                            raise RuntimeError('Unsafe archive path.')
                    source.extractall(staging)
            else:
                with tarfile.open(archive) as source:
                    source.extractall(staging,filter='data')
            destination.mkdir(parents=True,exist_ok=True)
            # No upstream shell or layout script is executed by this installer.
            shutil.copytree(staging,destination,symlinks=True,dirs_exist_ok=True)
        marker.write_text(package['sha256']+'\n')
        print(f'Installed {package["name"]}',flush=True)


def adjust_menu_opacity(data):
    """Raise the main popup backing layer to 96% while preserving glass borders."""
    path=data/'plasma/desktoptheme/Se7enAeroStyle/dialogs/background.svg'
    tree=ET.parse(path)
    backing=next((e for e in tree.getroot().iter() if e.get('id')=='rect1634'),None)
    if backing is None:
        raise RuntimeError('Reviewed theme popup backing layer is missing.')
    style=dict(part.split(':',1) for part in backing.get('style','').split(';') if ':' in part)
    if style.get('fill-opacity')=='0.96':
        return
    original=path.with_suffix('.svg.before-grandma')
    if not original.exists():
        shutil.copy2(path,original)
    style['fill-opacity']='0.96'
    style['fill']='#182c40'
    backing.set('style',';'.join(f'{key}:{value}' for key,value in style.items()))
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')
    tree.write(path,encoding='utf-8',xml_declaration=True)
