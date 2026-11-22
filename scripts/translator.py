#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install a pinned, CPU-only Argos environment without changing system Python."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

ROOT=Path(__file__).resolve().parent.parent
UV_URL='https://github.com/astral-sh/uv/releases/download/0.13.8/uv-x86_64-unknown-linux-gnu.tar.gz'
UV_SHA256='5acfd9177cfecf0bf87578f059728215ccc884388988f55f7a65041b57387d91'
ENV=dict(os.environ,ARGOS_CHUNK_TYPE='MINISBD',ARGOS_DEVICE_TYPE='cpu',ARGOS_INTRA_THREADS='2',
         ARGOS_INTER_THREADS='1',ARGOS_COMPUTE_TYPE='int8',OMP_NUM_THREADS='2')


def fetch(url,path,digest):
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==digest:return
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.partial')
    try:
        subprocess.run(['curl','-fsSL','--retry','2','--connect-timeout','30','--max-time','900','-o',str(temporary),url],check=True)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:raise RuntimeError('Download checksum mismatch: '+url)
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


def install_models():
    from argostranslate import package
    cache=Path.home()/'.cache/grandma-linux/translator'
    for model in json.loads((ROOT/'data/translation-sentence-models.json').read_text()):
        fetch(model['url'],Path.home()/'.local/share/argos-translate/minisbd'/model['name'],model['sha256'])
    for model in json.loads((ROOT/'data/translation-models.json').read_text()):
        installed=package.get_installed_packages()
        archive=cache/model['url'].rsplit('/',1)[-1]
        if any(p.from_code==model['from_code'] and p.to_code==model['to_code'] and p.package_version==model['package_version'] for p in installed):
            if archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest()==model['sha256']:archive.unlink()
            continue
        fetch(model['url'],archive,model['sha256'])
        package.install_from_path(archive)
        # Models are installed; do not keep a second compressed copy.
        archive.unlink()


def configure(dry_run=False):
    if dry_run:
        print('Install CPU-only Argos Translate and ten offline language models.');return
    base=Path.home()/'.local/share/grandma-linux/translator';base.mkdir(parents=True,exist_ok=True)
    uv=base/'uv'
    cache=Path.home()/'.cache/grandma-linux/translator'
    archive=cache/'uv-0.13.8.tar.gz';fetch(UV_URL,archive,UV_SHA256)
    with tarfile.open(archive) as tar:
        member=tar.extractfile('uv-x86_64-unknown-linux-gnu/uv')
        with uv.open('wb') as stream:shutil.copyfileobj(member,stream)
    uv.chmod(0o755)
    python=base/'venv/bin/python'
    if not python.exists():
        subprocess.run([str(uv),'venv','--python','3.12.16','--managed-python',str(base/'venv')],check=True,env=ENV)
    requirements=ROOT/'data/translator-requirements.txt'
    marker=base/'requirements.sha256';digest=hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not marker.exists() or marker.read_text()!=digest:
        subprocess.run([str(uv),'pip','sync','--python',str(python),'--require-hashes','--only-binary=:all:',
            '--index','https://download.pytorch.org/whl/cpu','--index-strategy','unsafe-best-match',str(requirements)],check=True,env=ENV)
        marker.write_text(digest)
    subprocess.run([str(python),str(Path(__file__).resolve()),'--install-models'],check=True,env=ENV)
    for name in ['translator-ui.py']:
        shutil.copyfile(ROOT/'scripts'/name,base/name)
    app=Path.home()/'.local/share/applications/grandma-translator.desktop';app.parent.mkdir(parents=True,exist_ok=True)
    if app.exists() and '# Grandma Linux managed' not in app.read_text():
        raise RuntimeError('Refusing to overwrite personal translator launcher')
    app.write_text('# Grandma Linux managed\n[Desktop Entry]\nType=Application\nName=Translator\nName[pt_BR]=Tradutor\n'
        f'Exec="{python}" "{base / "translator-ui.py"}"\nIcon=accessories-dictionary\nCategories=Utility;\nTerminal=false\n')
    subprocess.run(['update-desktop-database',str(app.parent)],check=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--dry-run',action='store_true');parser.add_argument('--install-models',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.install_models:install_models()
    else:configure(args.dry_run)
