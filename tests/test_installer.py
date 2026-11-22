#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import installer,profiles

class Installer(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.home/'.config'),'LANG':'en_US.UTF-8'});self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def invoke(self,*args):
        output=io.StringIO()
        with patch.object(sys,'argv',['installer',*args]),redirect_stdout(output),redirect_stderr(output):result=installer.main()
        return result,output.getvalue()
    def test_reboot_retains_desired_profile_and_success_updates_applied_state(self):
        previous=profiles.load(ROOT);profiles.private_json(profiles.manifest_path(),{'version':'0.0.1','profile':previous})
        custom=self.home/'custom.yaml';custom.write_text('features:\n  games: false\n  translator: false\n')
        calls=[]
        def run(command,**kwargs):
            if 'apply-profile.sh' in str(command):
                env=kwargs['env'];calls.append((command,env,Path(env['GRANDMA_APPS_MANIFEST']).read_text()))
                return subprocess.CompletedProcess(command,75 if len(calls)==1 else 0)
            return subprocess.CompletedProcess(command,0)
        with patch.object(installer,'check_platform'),patch.object(installer.subprocess,'run',side_effect=run),patch.object(profiles.subprocess,'check_output',return_value='{"filesystems":[]}'):
            code,_=self.invoke('--config',str(custom),'--yes')
            self.assertEqual(code,75);self.assertEqual(profiles.previous(),previous)
            self.assertFalse(profiles.read(profiles.profile_path())['features']['games'])
            custom.unlink() # A reboot/reinstallation must not need the original input file.
            code,_=self.invoke('--yes')
            self.assertEqual(code,0)
        self.assertFalse(profiles.previous()['features']['games'])
        self.assertFalse(profiles.previous()['features']['translator'])
        for command,env,manifest in calls:
            self.assertIn('--update',command)
            self.assertEqual(env['GRANDMA_GAMES'],'0');self.assertEqual(env['GRANDMA_TRANSLATOR'],'0')
            self.assertNotIn('org.kde.kpat|',manifest)
        statuses={json.loads(p.read_text())['status'] for p in (profiles.state_dir()/'profile-snapshots').glob('*.json')}
        self.assertEqual(statuses,{'complete','reboot-required'})
    def test_reinstallation_reuses_a_saved_profile_without_the_old_manifest(self):
        selected=profiles.merge(profiles.DEFAULT,{'features':{'games':False,'backup':False},'language':'pt-BR'})
        profiles.save(selected)
        with patch.object(installer,'check_platform'),patch.object(installer.subprocess,'run',return_value=subprocess.CompletedProcess([],0)),patch.object(profiles.subprocess,'check_output',return_value='{"filesystems":[]}'):
            code,output=self.invoke('--yes')
        self.assertEqual(code,0,output)
        self.assertEqual(profiles.previous()['language'],'pt-BR');self.assertFalse(profiles.previous()['features']['games'])
        self.assertFalse(profiles.previous()['features']['backup'])

    def test_snapshot_can_recover_from_an_invalid_current_yaml_without_mutation_in_preview(self):
        profile=profiles.load(ROOT);snapshot=profiles.begin(ROOT,profile,'install')
        profiles.profile_path().write_text('features:\n  ai: true\n')
        before=profiles.profile_path().read_bytes()
        code,output=self.invoke('--from-snapshot',snapshot.stem,'--dry-run')
        self.assertEqual(code,0,output);self.assertEqual(profiles.profile_path().read_bytes(),before)
        self.assertIn('"ai": false',output)
    def test_interactive_bootstrap_template_stops_and_prints_a_durable_command(self):
        with patch.object(Path,'cwd',return_value=self.home),patch.dict(os.environ,{'GRANDMA_BOOTSTRAP_REF':'main'}),patch('builtins.input',side_effect=['1','s','']):
            code,output=self.invoke('--interactive')
        self.assertEqual(code,0,output)
        self.assertTrue((self.home/'grandma-profile.yaml').exists())
        self.assertIn('curl -fsSL',output);self.assertNotIn(str(ROOT/'setup.sh'),output)
        self.assertFalse(profiles.state_dir().exists())
    def test_update_preview_never_starts_a_release_download(self):
        with patch.object(installer.subprocess,'run',side_effect=AssertionError('preview must be offline')):
            code,output=self.invoke('--mode','update','--dry-run')
        self.assertEqual(code,0,output)
    def test_template_preview_does_not_create_the_file(self):
        destination=self.home/'not-created.yaml'
        code,output=self.invoke('--template',str(destination),'--dry-run')
        self.assertEqual(code,0,output);self.assertFalse(destination.exists())

    def test_first_install_defaults_to_english_on_a_portuguese_host(self):
        with patch.dict(os.environ,{'LANG':'pt_BR.UTF-8'}),patch('builtins.input',side_effect=['1','n']):
            code,output=self.invoke('--interactive','--dry-run')
        self.assertEqual(code,0,output)
        self.assertIn('Grandma Linux · Installer',output)
        self.assertIn('"language": "en"',output)

    def test_unknown_profile_fields_fail_before_state_creation(self):
        path=self.home/'bad.yaml';path.write_text('unknown: true\n')
        code,output=self.invoke('--config',str(path),'--yes')
        self.assertEqual(code,2);self.assertFalse(profiles.state_dir().exists())

if __name__=='__main__':unittest.main()
