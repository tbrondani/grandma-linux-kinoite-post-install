#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read-only size inventory. Run before and after setup to measure the difference."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(os.environ, LC_ALL='C')


def run(*args):
    return subprocess.check_output(args, text=True, env=ENV, stderr=subprocess.DEVNULL).strip()


def disk_sizes(paths):
    paths = [str(p) for p in paths if p.exists()]
    if not paths:
        return {}
    # One du process counts shared hard links only once across all listed paths.
    return {line.split('\t', 1)[1]: int(line.split('\t', 1)[0])
            for line in run('du', '-sx', '-B1', *paths).splitlines()}


def human_bytes(value):
    match = re.fullmatch(r'([0-9.,]+)\s*(bytes|kB|MB|GB|TB)', value.strip())
    return int(float(match[1].replace(',', '')) * 1000 ** ['bytes', 'kB', 'MB', 'GB', 'TB'].index(match[2])) if match else None


def collect():
    flatpaks = []
    for scope in ['user', 'system']:
        for ref in run('flatpak', 'list', '--'+scope, '--all', '--columns=ref').splitlines():
            origin = run('flatpak', 'info', '--'+scope, '--show-origin', ref)
            commit = run('flatpak', 'info', '--'+scope, '--show-commit', ref)
            item = dict(scope=scope, ref=ref, commit=commit,
                        installed_bytes=int(run('flatpak', 'info', '--'+scope, '--show-size', ref)),
                        download_bytes_estimate=None)
            try:
                remote = run('flatpak', 'remote-info', '--'+scope, '--commit='+commit, origin, ref)
                match = re.search(r'Download Size:\s*([^\n]+)', remote)
                if match: item['download_bytes_estimate'] = human_bytes(match[1])
            except subprocess.CalledProcessError:
                pass
            flatpaks.append(item)
    home = Path.home()
    paths = [home/'.local/share/flatpak', Path('/var/lib/flatpak'), home/'.var/app',
             home/'.local/share/grandma-linux/translator', home/'.local/share/argos-translate',
             home/'.local/share/uv', home/'.cache/uv', home/'.cache/grandma-linux',
             home/'.local/share/plasma', home/'.local/share/aurorae', home/'.local/share/icons',
             home/'.local/share/color-schemes', home/'.local/share/grandma-linux/backups',
             home/'.local/libexec/grandma-linux', home/'.cache/restic']
    assets = []
    for p in json.loads((ROOT/'data/dictionaries.json').read_text()):
        folder=home/'.var/app/com.ktechpit.omnidict/data/ktechpit/omnidict/dictionaries'/p['dict_id']/p['version']
        cached=home/'.cache/grandma-linux/dictionaries'/f'{p["dict_id"]}-{p["sha256"]}.download'
        assets.append(dict(kind='dictionary',name=p['dict_id'],download_bytes=p.get('size_compressed',cached.stat().st_size if cached.is_file() else None),
                           installed_bytes=sum(f.stat().st_size for f in folder.rglob('*') if f.is_file())))
    for p in json.loads((ROOT/'data/themes.json').read_text()):
        assets.append(dict(kind='theme',name=p['name'],download_bytes=p['size']))
    for folder in ['OMaps','OrganicMaps']:
        for p in (home/'.var/app/app.organicmaps.desktop/data'/folder).glob('*/*.mwm'):
            assets.append(dict(kind='map',name=p.stem,download_bytes=p.stat().st_size,installed_bytes=p.stat().st_size))
    model_manifest=ROOT/'data/translation-models.json'
    if model_manifest.exists():
        for p in json.loads(model_manifest.read_text()):
            folder=home/'.local/share/argos-translate/packages'
            candidates=[f.parent for f in folder.glob('*/metadata.json') if (lambda m: m.get('from_code')==p['from_code'] and m.get('to_code')==p['to_code'])(json.loads(f.read_text()))]
            assets.append(dict(kind='translation model',name=p['code'],download_bytes=p['download_bytes'],
                installed_bytes=sum(f.stat().st_size for d in candidates for f in d.rglob('*') if f.is_file())))
    sentence_manifest=ROOT/'data/translation-sentence-models.json'
    if sentence_manifest.exists():
        for p in json.loads(sentence_manifest.read_text()):
            path=home/'.local/share/argos-translate/minisbd'/p['name']
            assets.append(dict(kind='sentence model',name=p['name'],download_bytes=p['download_bytes'],installed_bytes=path.stat().st_size if path.is_file() else None))
    packages=[]
    for line in run('rpm','-q','--qf','%{NAME}\t%{VERSION}-%{RELEASE}\t%{SIZE}\n',
                    'vim-enhanced','vim-common','vim-filesystem','restic','fastfetch','b3sum','yyjson','kdialog','fuse','python3-dbus','python3-gobject-base').splitlines():
        name,version,size=line.split('\t');packages.append(dict(name=name,version=version,installed_bytes=int(size)))
    fs=os.statvfs(home)
    return dict(date=datetime.now(timezone.utc).isoformat(),os=run('cat','/etc/os-release'),
                filesystem_used_bytes=(fs.f_blocks-fs.f_bfree)*fs.f_frsize,
                allocated_bytes_by_path=disk_sizes(paths),flatpaks=flatpaks,assets=assets,system_packages=packages,
                notes=['Flatpak installed sizes are logical per-ref sizes; do not sum them as physical disk use.',
                       'Download estimates come from rounded remote metadata for the installed commit, not measured traffic.',
                       'Assets are already included in directory sizes. Do not add both totals.',
                       'A before/after filesystem difference includes unrelated VM changes; use a clean baseline.'])


def markdown(report):
    mb=lambda n: 'unknown' if n is None else f'{n/1e6:.1f}'
    lines=['# Installation size inventory','',f'Measured: {report["date"]}. Sizes below use decimal MB.','',
           'Download values for Flatpaks are estimates. Shared runtimes appear once per installation scope. Logical installed sizes can share files; they are not additional disk use.','',
           '| Scope | Flatpak ref | Download MB (estimate) | Installed MB (logical) |','|---|---|---:|---:|']
    for p in report['flatpaks']:lines.append(f'| {p["scope"]} | {p["ref"]} | {mb(p["download_bytes_estimate"])} | {mb(p["installed_bytes"])} |')
    lines+=['','| Data | Item | Download MB | Installed MB (logical) |','|---|---|---:|---:|']
    for p in report['assets']:lines.append(f'| {p["kind"]} | {p["name"]} | {mb(p.get("download_bytes"))} | {mb(p.get("installed_bytes"))} |')
    lines+=['','| Directory | Allocated MB |','|---|---:|']
    for path,size in report['allocated_bytes_by_path'].items():lines.append(f'| {path.replace(str(Path.home()),"~")} | {mb(size)} |')
    lines+=['','Native package sizes (logical installed bytes):','']
    for p in report['system_packages']:lines.append(f'- {p["name"]} {p["version"]}: {mb(p["installed_bytes"])} MB')
    lines+=['']+['- '+note for note in report['notes']]
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--markdown',type=Path)
    parser.add_argument('--before',type=Path)
    args=parser.parse_args();report=collect()
    if args.before:
        before=json.loads(args.before.read_text());report['filesystem_delta_bytes']=report['filesystem_used_bytes']-before['filesystem_used_bytes']
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.markdown:args.markdown.write_text(markdown(report))
