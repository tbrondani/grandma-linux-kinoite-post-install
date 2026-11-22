#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Download installed Organic Maps catalogue regions, without GUI automation."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

APP = 'app.organicmaps.desktop'


def read_catalogue():
    for filename in ['countries.json','countries.txt']:
        try:
            raw=subprocess.check_output(['flatpak','run','--command=cat',APP,
                '/app/share/organicmaps/data/'+filename],stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            continue
        catalogue=json.loads(raw)
        if not isinstance(catalogue,dict) or not isinstance(catalogue.get('g'),list) or 'v' not in catalogue:
            raise ValueError('Unsupported Organic Maps catalogue')
        return catalogue
    raise RuntimeError('Cannot read the installed Organic Maps catalogue (countries.json or countries.txt)')


def map_directory(catalogue):
    data=Path.home()/'.var/app'/APP/'data'
    if (data/'OrganicMaps').is_dir():return data/'OrganicMaps'
    if (data/'OMaps').exists():return data/'OMaps'
    # Modern releases migrate OMaps to OrganicMaps. Their catalogue uses BLAKE3.
    return data/('OrganicMaps' if any('h' in leaf for leaf in leaves(catalogue)) else 'OMaps')


def leaves(node):
    if 'g' in node:
        for child in node['g']:
            yield from leaves(child)
    elif 's' in node:
        yield node


def select(catalogue, regions):
    result = {}
    def visit(node):
        if node['id'] in regions:
            result.update((leaf['id'], leaf) for leaf in leaves(node))
        for child in node.get('g', []):
            visit(child)
    visit(catalogue)
    for region in regions:
        if not any(leaf['id'] == region or leaf['id'].startswith(region + '_') for leaf in result.values()):
            raise ValueError(f'Unknown or empty map region: {region}')
    return list(result.values())


def valid(path, leaf):
    if not path.is_file() or path.stat().st_size != leaf['s']:
        return False
    if 'h' in leaf:
        expected=base64.b64decode(leaf['h'],validate=True)
        if len(expected)!=9:raise ValueError('Unsupported map BLAKE3 digest length')
        output=subprocess.check_output(['b3sum','--length','9','--no-names',str(path)],text=True)
        return bytes.fromhex(output.strip())==expected
    if 'sha1_base64' not in leaf:raise ValueError('Map catalogue has no supported integrity hash')
    digest = hashlib.sha1()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return base64.b64encode(digest.digest()).decode() == leaf['sha1_base64']


def download(leaf, version, destination, servers):
    name = leaf['id']
    if Path(name).name != name or name in ('.', '..'):
        raise ValueError('Unsafe map name in catalogue')
    target = destination / f'{name}.mwm'
    if valid(target, leaf):
        print(f'Map already verified: {name}', flush=True)
        return
    partial = target.with_suffix('.mwm.partial')
    failures = []
    for server in servers:
        if not server.startswith('https://'):
            continue
        url = server.rstrip('/') + f'/maps/{version}/' + urllib.parse.quote(name) + '.mwm'
        try:
            print(f'Downloading map: {name} ({leaf["s"] / 1e6:.1f} MB)', flush=True)
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'curl/8.0'}), timeout=90) as response, partial.open('wb') as output:
                size = 0
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > leaf['s']:
                        raise ValueError('Map exceeds catalogue size')
                    output.write(block)
            if not valid(partial, leaf):
                raise ValueError('Map size or integrity hash differs from installed catalogue')
            partial.replace(target)
            return
        except (OSError, ValueError) as error:
            failures.append(f'{server}: {error}')
        finally:
            partial.unlink(missing_ok=True)
    raise RuntimeError(f'Cannot download {name}: ' + '; '.join(failures))


def configure(regions=None, dry_run=False):
    config = json.loads((Path(__file__).resolve().parent.parent / 'data/offline-regions.json').read_text())
    regions = regions or config['download_regions']
    if dry_run:
        print('Offline maps: ' + ', '.join(regions))
        return
    # Read the app's catalogue instead of guessing a compatible map release.
    catalogue = read_catalogue()
    selected = select(catalogue, regions)
    version = str(catalogue['v'])
    if not version.isdigit():
        raise ValueError('Invalid map version')
    with urllib.request.urlopen(urllib.request.Request('https://meta.omaps.app/maps', headers={'User-Agent': 'curl/8.0'}), timeout=30) as response:
        metadata = json.load(response)
    servers = metadata if isinstance(metadata, list) else metadata['servers']
    root = map_directory(catalogue)
    destination = root / version
    destination.mkdir(parents=True, exist_ok=True)
    for leaf in selected:
        download(leaf, version, destination, servers)
    print(f'Offline maps verified: {len(selected)} files, catalogue {version}. Restart Maps to load them.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--region', action='append', help='Catalogue region ID; repeat for multiple regions')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    configure(args.region, args.dry_run)
