#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the real updater with a local release fixture in the test VM only."""
import difflib
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import project_update as update

if os.environ.get('GRANDMA_TEST_VM')!='1':raise SystemExit('Run only in the disposable Grandma Linux test VM.')
environment=subprocess.check_output(['systemctl','--user','show-environment'],text=True)
for line in environment.splitlines():
    if '=' in line:
        key,value=line.split('=',1);values=shlex.split(value);os.environ[key]=values[0] if len(values)==1 else value
os.environ['GRANDMA_TEST_VM']='1'
config=Path.home()/'.config'
paths=[config/'kdeglobals',config/'kwinrc',config/'plasma-org.kde.plasma.desktop-appletsrc',config/'grandma-linux/backup.json']
def settings(path):
    # Plasma updates icon positions while it watches desktop file events.
    # Compare appearance and panel settings, excluding that live cache.
    return b'\n'.join(line for line in path.read_bytes().splitlines() if not line.startswith((b'positions=',b'changedPositions=',b'screenMapping=')))
before={str(path):settings(path) for path in paths if path.is_file()}
desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
marker=Path.home()/'grandma-update-preservation-test.txt'
if marker.exists():raise SystemExit('Test marker already exists; refusing to replace it.')
marker.write_text('Keep this personal file.\n')
try:
    with tempfile.TemporaryDirectory(prefix='grandma-update-fixture-') as folder:
        folder=Path(folder);archive=folder/'release.tar.gz';tag='v0.1.0'
        with tarfile.open(archive,'w:gz') as tar:
            for directory in ['scripts','data','docs','assets']:
                tar.add(ROOT/directory,arcname='grandma-linux-'+tag+'/'+directory,filter=lambda member: None if '__pycache__' in member.name else member)
            tar.add(ROOT/'setup.sh',arcname='grandma-linux-'+tag+'/setup.sh')
            data=b'0.1.0\n';member=tarfile.TarInfo('grandma-linux-'+tag+'/VERSION');member.size=len(data);tar.addfile(member,io.BytesIO(data))
        release=dict(available=True,tag=tag,current=update.installed_version(),url='https://fixture.invalid/release',size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        # Replace transport only. Keep actual SHA256 checks, extraction, setup,
        # version recording and application installation unchanged.
        with patch.object(update.urllib.request,'build_opener') as opener:
            opener.return_value.open.side_effect=lambda *args,**kwargs:archive.open('rb')
            code=update.apply(release,'pt-BR')
        if code:raise SystemExit('Update did not finish: '+str(code))
        assert update.installed_version()=='0.1.0'
        assert marker.read_text()=='Keep this personal file.\n'
        for name,content in before.items():
            after=settings(Path(name))
            if after!=content:
                print(''.join(difflib.unified_diff(content.decode().splitlines(True),after.decode().splitlines(True),fromfile=name+' before',tofile=name+' after')),flush=True)
                raise AssertionError('Changed personal setting: '+name)
        print(json.dumps(dict(status='passed',transport='local fixture; not a published GitHub release',version=update.installed_version(),preserved_settings=list(before)),indent=2))
finally:marker.unlink(missing_ok=True)
