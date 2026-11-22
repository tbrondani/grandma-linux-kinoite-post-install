#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prepare/resume a test update across a real VM reboot. No OS packages changed."""
import argparse
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

if os.environ.get('GRANDMA_TEST_VM')!='1':raise SystemExit('Only run in the disposable test VM.')
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=['prepare','resume']);args=parser.parse_args()
for line in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines():
    if '=' in line:
        key,value=line.split('=',1);parsed=shlex.split(value);os.environ[key]=parsed[0] if len(parsed)==1 else value
context=ROOT/'update-reboot-context.json';marker=ROOT/'update-reboot-marker'

if args.phase=='prepare':
    if context.exists() or marker.exists() or update.pending_update():raise SystemExit('A test or update is already pending.')
    previous=update.version_tuple(update.installed_version()) or (0,1,0)
    version='.'.join(map(str,(*previous[:2],previous[2]+1)));tag='v'+version
    with tempfile.TemporaryDirectory() as folder:
        archive=Path(folder)/'release.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for directory in ['scripts','data','docs','assets']:
                tar.add(ROOT/directory,arcname='grandma-linux-'+tag+'/'+directory,filter=lambda member:None if '__pycache__' in member.name else member)
            # Stop once at the reboot boundary, then run the real setup after
            # the host operator reboots the VM. Only this fixture has the shim.
            prefix='if [[ ! -e '+shlex.quote(str(marker))+' ]]; then : > '+shlex.quote(str(marker))+'; exit 75; fi\n'
            for name,data in [('setup.sh',prefix.encode()+(ROOT/'setup.sh').read_bytes()),('VERSION',(version+'\n').encode())]:
                member=tarfile.TarInfo('grandma-linux-'+tag+'/'+name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
        descriptor=dict(available=True,tag=tag,url=f'https://github.com/{update.REPOSITORY}/releases/download/{tag}/grandma-linux-{tag}.tar.gz',sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),size=archive.stat().st_size)
        with patch.object(update.urllib.request,'build_opener') as opener:
            opener.return_value.open.side_effect=lambda *args,**kwargs:archive.open('rb')
            assert update.apply(descriptor,'pt-BR')==75
        assert update.pending_update()['phase']=='reboot-required'
        before=update.installed_version()
        result=subprocess.run([str(Path.home()/'.local/bin/grandma-update'),'--apply','--yes','--lang=pt-BR'],capture_output=True,text=True)
        assert result.returncode==75,result.stdout+result.stderr
        assert update.installed_version()==before
        context.write_text(json.dumps(dict(version=version,boot_id=update.boot_id(),previous=before),indent=2))
        print('Reboot boundary saved; same-boot retry correctly returned 75. Reboot the VM, then run resume.')
else:
    expected=json.loads(context.read_text())
    assert update.boot_id()!=expected['boot_id'],'Reboot the VM before resuming'
    result=subprocess.run([str(Path.home()/'.local/bin/grandma-update'),'--apply','--yes','--lang=pt-BR'],capture_output=True,text=True)
    print(result.stdout,flush=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'download' not in result.stdout,'The verified package must be reused'
    assert update.installed_version()==expected['version']
    assert not update.pending_path().exists() and not update.archive_path().exists()
    marker.unlink();context.unlink()
    update.record_install(ROOT)
    print(json.dumps(dict(status='passed',real_reboot=True,cli_resume=True,reused_verified_package=True,version=expected['version']),indent=2))
