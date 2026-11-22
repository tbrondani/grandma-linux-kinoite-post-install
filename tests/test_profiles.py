#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import copy
import json
import os
from pathlib import Path
import subprocess
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import profiles

class Profiles(unittest.TestCase):
    def test_language_change_requires_separate_consent(self):
        for current,requested in [('en','pt-BR'),('pt-BR','en')]:
            for answer in ('n',''):
                with patch('builtins.input',return_value=answer):
                    self.assertEqual(profiles.confirm_language(requested,current,True),current)
            with patch('builtins.input',return_value='yes'):
                self.assertEqual(profiles.confirm_language(requested,current,True),requested)
            with patch('builtins.input',side_effect=AssertionError('no terminal')):
                self.assertEqual(profiles.confirm_language(requested,current,False),current)
                self.assertEqual(profiles.confirm_language(current,current,True),current)
                self.assertEqual(profiles.confirm_language(requested,None,True),requested)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.home=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'HOME':str(self.home),'XDG_CONFIG_HOME':str(self.home/'.config')});self.env.start()
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_default_parity_and_template_roundtrip(self):
        value=profiles.load(ROOT)
        self.assertEqual(len(profiles.selected(ROOT,value)),len(profiles.all_apps(ROOT)))
        self.assertFalse(value['features']['ai']);self.assertTrue(value['vm']['autologin'])
        self.assertEqual(profiles.parse(profiles.dump(value)),value)
        self.assertEqual(profiles.validate(profiles.merge(profiles.DEFAULT,profiles.parse((ROOT/'data/profile.example.yaml').read_text())),ROOT),value)
    def test_duplicate_unsafe_and_non_boolean_values_fail(self):
        for source in ['features:\n  games: true\n  games: false\n','features:\n  games: !!python/object x\n','features:\n\tgames: false\n','features:\n   games: false\n']:
            with self.assertRaises(profiles.ProfileError):profiles.parse(source)
        for changes in [{'features':{'games':'false'}},{'schema_version':True},{'schema_version':2},{'features':{'ai':True}},{'language':'fr'},{'environment':{'PATH':'/tmp'}},{'environment':{'API_KEY':'secret'}},{'applications':{'unknown':False}}]:
            with self.assertRaises(profiles.ProfileError):profiles.validate(profiles.merge(profiles.DEFAULT,changes),ROOT)
    def test_malformed_nested_maps_are_configuration_errors(self):
        path=self.home/'invalid.yaml'
        for field in ['features','environment','applications','system','storage','vm']:
            path.write_text(field+': false\n')
            with self.assertRaises(profiles.ProfileError):profiles.load(ROOT,path)

    def test_partial_profiles_saved_choices_and_new_fields(self):
        selected=profiles.merge(profiles.DEFAULT,{'features':{'games':False,'translator':False},'language':'pt-BR'})
        profiles.save(selected)
        path=self.home/'custom.yaml';path.write_text('features:\n  backup: false\n')
        result=profiles.load(ROOT,path)
        self.assertFalse(result['features']['games']);self.assertFalse(result['features']['backup']);self.assertFalse(result['features']['translator'])
        self.assertEqual(result['language'],'pt-BR')
        prior=copy.deepcopy(selected);del prior['features']['accessibility'];profiles.profile_path().write_text(profiles.dump(prior))
        self.assertFalse(profiles.load(ROOT)['features']['accessibility'])
    def test_manually_saved_partial_profile_keeps_initial_defaults(self):
        path=profiles.profile_path();path.parent.mkdir(parents=True)
        path.write_text('language: pt-BR\nfeatures:\n  games: false\n')
        profile=profiles.load(ROOT)
        self.assertFalse(profile['features']['games'])
        self.assertTrue(profile['features']['translator']);self.assertTrue(profile['features']['backup'])

    def test_environment_removal_is_preserved_on_later_runs(self):
        selected=profiles.merge(profiles.DEFAULT,{'environment':{'MY_NOTE':'one','MY_OTHER':'two'}})
        profiles.save(selected);profiles.private_json(profiles.manifest_path(),{'profile':selected})
        path=self.home/'custom.yaml';path.write_text('environment:\n  MY_NOTE: null\n')
        changed=profiles.load(ROOT,path);self.assertNotIn('MY_NOTE',changed['environment'])
        self.assertEqual(changed['environment']['MY_OTHER'],'two')
        profiles.save(changed)
        self.assertNotIn('MY_NOTE',profiles.load(ROOT)['environment'])
        path.write_text('environment: {}\n');self.assertEqual(profiles.load(ROOT,path)['environment'],{})

    def test_selection_does_not_propose_removing_existing_data(self):
        value=profiles.merge(profiles.DEFAULT,{'features':{'games':False,'offline_maps':False,'remote_support':False}})
        plan=profiles.plan(ROOT,value)
        self.assertEqual(plan['removals'],[])
        self.assertNotIn('app.organicmaps.desktop',plan['applications'])
        self.assertNotIn('com.rustdesk.RustDesk',plan['applications'])
        self.assertFalse(profiles.GAME_IDS&set(plan['applications']))
        self.assertIn('com.brave.Browser',plan['applications'])
    def test_snapshot_history_keeps_applied_state_on_failure(self):
        value=profiles.load(ROOT);profiles.private_json(profiles.manifest_path(),{'version':'0.1.0','profile':value})
        profiles.save(value)
        with profiles.profile_path().open('a') as stream:stream.write('# Personal notes are retained in history\n')
        changed=profiles.merge(value,{'features':{'games':False}})
        snapshot=profiles.begin(ROOT,changed,'reconfigure');profiles.finish(snapshot,'failed',ROOT,changed,1)
        self.assertEqual(profiles.previous(),value)
        self.assertFalse(profiles.read(profiles.profile_path())['features']['games'])
        self.assertEqual(json.loads(snapshot.read_text())['status'],'failed')
        self.assertIn('Personal notes',json.loads(snapshot.read_text())['saved_preferences_text'])
        self.assertEqual(snapshot.stat().st_mode&0o777,0o600)
    def test_username_and_mount_assertions_never_change_the_host(self):
        value=profiles.merge(profiles.DEFAULT,{'system':{'username':'different-user'}})
        with self.assertRaises(profiles.ProfileError):profiles.check_identity(value)
        value=profiles.merge(profiles.DEFAULT,{'storage':{'mount_points':{'home':str(self.home/'not-a-mount')}}})
        with self.assertRaises(profiles.ProfileError):profiles.check_identity(value)
    def test_cli_preview_is_offline_and_template_never_overwrites(self):
        path=self.home/'profile.yaml';path.write_text('features:\n  games: false\n  translator: false\n')
        command=['bash',str(ROOT/'setup.sh'),'--config',str(path),'--dry-run']
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        plan=json.loads(result.stdout.split('\n',1)[1]);self.assertFalse(plan['profile']['features']['games'])
        self.assertFalse(profiles.state_dir().exists());self.assertFalse(profiles.profile_path().exists())
        created=self.home/'template.yaml'
        result=subprocess.run(['bash',str(ROOT/'setup.sh'),'--template',str(created)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        before=created.read_bytes()
        result=subprocess.run(['bash',str(ROOT/'setup.sh'),'--template',str(created)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual(created.read_bytes(),before)
    def test_component_guards_reach_the_backend_without_optional_downloads(self):
        value=profiles.merge(profiles.DEFAULT,{'features':{key:False for key in profiles.FEATURES}})
        manifest=self.home/'apps.tsv';manifest.write_text(''.join('|'.join(row)+'\n' for row in profiles.selected(ROOT,value)))
        environment=dict(os.environ,GRANDMA_PROFILE_JSON=json.dumps(value),GRANDMA_APPS_MANIFEST=str(manifest))
        for key in value['features']:environment['GRANDMA_'+key.upper()]='0'
        result=subprocess.run(['bash',str(ROOT/'scripts/apply-profile.sh'),'--dry-run','--update'],env=environment,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertNotIn('org.kde.kpat',result.stdout)
        self.assertNotIn('restic',result.stdout)
        self.assertNotIn('Portugal maps are ready',result.stdout)
        self.assertIn('com.brave.Browser',result.stdout)

    def test_environment_is_quoted_data_and_reserved_names_are_rejected(self):
        value=profiles.merge(profiles.DEFAULT,{'environment':{'GRANDMA_EXAMPLE':'x'}})
        with self.assertRaises(profiles.ProfileError):profiles.validate(value,ROOT)
        value=profiles.merge(profiles.DEFAULT,{'environment':{'MY_EXAMPLE':'$(touch /tmp/never-execute) $VALUE'}})
        profiles.validate(value,ROOT)
        with patch.object(profiles.subprocess,'run'):
            profiles.install_environment(value)
        data=(self.home/'.config/environment.d/90-grandma-linux.conf').read_text()
        self.assertIn('$$VALUE',data);self.assertIn('MY_EXAMPLE=',data)

    def test_environment_generator_keeps_literal_dollars_and_quotes(self):
        generator=Path('/usr/lib/systemd/user-environment-generators/30-systemd-environment-d-generator')
        if not generator.is_file():self.skipTest('systemd environment generator is unavailable')
        literal='literal $VALUE $(touch '+str(self.home/'never-executed')+') "texto"'
        profile=profiles.merge(profiles.DEFAULT,{'environment':{'MY_EXAMPLE':literal}})
        with patch.object(profiles.subprocess,'run'):profiles.install_environment(profile)
        result=subprocess.run([str(generator)],capture_output=True,text=True,check=True)
        values=dict(token.split('=',1) for token in shlex.split(result.stdout) if '=' in token)
        # The generator emits shell-style quoting. Python shlex deliberately
        # keeps the backslash in \$ and \`, unlike the shell's double quotes.
        decoded=values['MY_EXAMPLE'].replace('\\$','$').replace('\\`','`')
        self.assertEqual(decoded,literal)
        self.assertFalse((self.home/'never-executed').exists())

if __name__=='__main__':unittest.main()
