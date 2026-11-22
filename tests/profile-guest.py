#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reconfigure, retry, update and restore a disposable guest without erasing data."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import profiles

if os.environ.get('GRANDMA_TEST_VM')!='1':raise SystemExit('Run only in the disposable Grandma Linux VM.')
for line in subprocess.check_output(['systemctl','--user','show-environment'],text=True).splitlines():
    if '=' in line:
        key,value=line.split('=',1);parsed=shlex.split(value);os.environ[key]=parsed[0] if len(parsed)==1 else value
original=profiles.load(ROOT)
marker=Path.home()/'grandma-profile-preservation-test.txt'
if marker.exists():raise SystemExit('Test marker already exists; refusing to replace it.')
marker.write_text('Preserve this personal file.\n')
config=Path.home()/'.config'
protected=[config/'kdeglobals',config/'kwinrc',config/'grandma-linux/backup.json']
before={str(path):path.read_bytes() for path in protected if path.is_file()}
maps=Path.home()/'.var/app/app.organicmaps.desktop'
map_files=list(maps.rglob('*.mwm'))
dictionaries=list((Path.home()/'.var/app/com.ktechpit.omnidict').rglob('dict.sqlite'))
retained={str(path):(path.stat().st_size,path.stat().st_mtime_ns) for path in map_files+dictionaries}
restored=False

def run(*args,expected=0):
    result=subprocess.run(['bash',str(ROOT/'setup.sh'),'--yes','--no-interactive',*args])
    if result.returncode!=expected:raise RuntimeError('Installer returned '+str(result.returncode))

try:
    with tempfile.TemporaryDirectory(prefix='grandma-profile-test-') as folder:
        folder=Path(folder);source=folder/'selected.yaml';restore=folder/'original.yaml'
        restore.write_text(profiles.dump(original))
        source.write_text('features:\n  games: false\n  translator: false\n  dictionaries: false\n  offline_maps: false\n  remote_support: false\n  backup: false\nenvironment:\n  MY_PROFILE_EXAMPLE: "literal$VALUE"\n')
        run('--mode','reconfigure','--config',str(source))
        chosen=profiles.previous()
        for key in ['games','translator','dictionaries','offline_maps','remote_support','backup']:assert chosen['features'][key] is False,key
        timer=subprocess.run(['systemctl','--user','is-active','--quiet','grandma-backup.timer'])
        assert timer.returncode!=0,'Disabled profile must stop the project backup timer'
        assert '$$VALUE' in (config/'environment.d/90-grandma-linux.conf').read_text()
        source.unlink();run('--mode','reconfigure') # The original input is no longer needed.
        assert not profiles.previous()['features']['games']
        invalid=folder/'invalid.yaml';invalid.write_text('features:\n  ai: true\n')
        saved=profiles.profile_path().read_bytes();run('--config',str(invalid),expected=2)
        assert profiles.profile_path().read_bytes()==saved
        # A real update from a local release transport fixture must preserve toggles.
        subprocess.run([sys.executable,str(ROOT/'tests/update-guest.py')],check=True)
        assert not profiles.previous()['features']['games']
        assert not profiles.previous()['features']['backup']
        assert marker.read_text()=='Preserve this personal file.\n'
        for name,(size,mtime) in retained.items():
            path=Path(name);assert path.is_file() and (path.stat().st_size,path.stat().st_mtime_ns)==(size,mtime),name
        for name,data in before.items():assert Path(name).read_bytes()==data,'Personal setting changed: '+name
        run('--mode','reconfigure','--config',str(restore));restored=True
        assert profiles.previous()==original
        if original['features']['backup']:
            subprocess.run(['systemctl','--user','is-active','--quiet','grandma-backup.timer'],check=True)
        assert marker.read_text()=='Preserve this personal file.\n'
        history=[json.loads(path.read_text()) for path in (profiles.state_dir()/'profile-snapshots').glob('*.json')]
        assert any(record['status']=='complete' and not record['desired']['features']['games'] for record in history)
        print(json.dumps(dict(status='passed',selected_profile=True,input_file_not_needed_on_repeat=True,invalid_config_before_changes=True,update_preserved_choices=True,retained_data_files=len(retained),appearance_and_backup_settings_preserved=True,original_profile_restored=True),indent=2))
finally:
    if not restored:
        # Restore preferences only; retain the failed operation logs for diagnosis.
        profiles.save(original)
    marker.unlink(missing_ok=True)
