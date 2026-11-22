#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use real restic in temporary repositories. Never touch a user's backup."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from backup import Backup

@unittest.skipUnless(shutil.which('restic'),'restic is required for integration tests')
class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        home=self.root/'home';home.mkdir()
        self.source=home/'Documentos';self.source.mkdir()
        self.backup=Backup(home)
        self.backup.sources=lambda:[self.source.resolve()]
        self.repository=home/'.local/share/grandma-linux/backups/local'
        self.file=self.source/'family photo.txt';self.file.write_text('original bytes\n')
    def tearDown(self):self.temp.cleanup()

    def test_copy_restore_and_repeat_configuration(self):
        config=self.backup.configure_local();key=(self.repository/'recovery-key.txt').read_bytes()
        self.backup.run();snapshot=self.backup.snapshots()[0]['id']
        self.file.write_text('new live data\n')
        restored=self.backup.restore(snapshot,self.root)
        self.assertEqual(self.file.read_text(),'new live data\n')
        self.assertEqual((restored/self.source.name/self.file.name).read_text(),'original bytes\n')
        self.assertEqual(self.backup.configure_local(),config)
        self.assertEqual((self.repository/'recovery-key.txt').read_bytes(),key)
        self.assertEqual((self.repository/'recovery-key.txt').stat().st_mode&0o777,0o600)
        self.assertIsNone(json.loads(self.backup.status_path.read_text())['error'])

    def test_profile_is_backed_up_and_recovered_without_overwriting_live_preferences(self):
        self.backup.sources=Backup.sources.__get__(self.backup,Backup)
        profile=self.backup.config_dir/'profile.yaml';profile.parent.mkdir(parents=True)
        original='schema_version: 1\nfeatures:\n  games: false\n';profile.write_text(original)
        with patch('backup.subprocess.check_output',return_value=str(self.source)):
            self.backup.configure_local();self.backup.run()
        snapshot=self.backup.snapshots()[0]['id'];profile.write_text('new live preferences')
        restored=self.backup.restore(snapshot,self.root)
        self.assertEqual((restored/'.config/grandma-linux/profile.yaml').read_text(),original)
        self.assertEqual(profile.read_text(),'new live preferences')

    def test_retention_leaves_foreign_snapshots(self):
        config=self.backup.configure_local()
        foreign=json.loads(self.backup.restic(config,'backup','--json','--tag','other-project','--',str(self.source)).splitlines()[-1])['snapshot_id']
        self.backup.run()
        remaining=json.loads(self.backup.restic(config,'snapshots','--json'))
        self.assertTrue(any(s['id'].startswith(foreign) for s in remaining))
        with self.assertRaises(ValueError):self.backup.restore(next(s['id'] for s in remaining if s['id'].startswith(foreign)),self.root)

    def test_repository_inside_source_is_rejected(self):
        with self.assertRaises(ValueError):self.backup.configure_local(self.source/'backup')
        self.assertFalse((self.source/'backup').exists())
        self.assertEqual(self.file.read_text(),'original bytes\n')

    def test_existing_unrelated_folder_is_preserved(self):
        other=self.root/'existing';other.mkdir();(other/'personal.txt').write_text('keep')
        with self.assertRaises(ValueError):self.backup.configure_local(other)
        self.assertEqual((other/'personal.txt').read_text(),'keep')

    def test_init_failure_can_be_retried(self):
        with patch.object(self.backup,'restic',side_effect=RuntimeError('failed init')):
            with self.assertRaises(RuntimeError):self.backup.configure_local()
        self.assertFalse((self.repository/'recovery-key.txt').exists())
        self.backup.configure_local();self.assertTrue((self.repository/'repository/config').is_file())

    def test_missing_repository_is_not_recreated(self):
        self.backup.configure_local();self.backup.run()
        saved=self.repository.with_name('disconnected');self.repository.rename(saved)
        with self.assertRaises(ValueError):self.backup.run()
        self.assertFalse(self.repository.exists())
        self.assertTrue(json.loads(self.backup.status_path.read_text())['last_success'])
        self.assertTrue(json.loads(self.backup.status_path.read_text())['error'])

    def test_existing_bundle_works_after_reinstall(self):
        config=self.backup.configure_local();self.backup.run()
        replacement=Backup(self.root/'new-home');replacement.sources=lambda:[self.source]
        replacement.configure_local(self.repository)
        self.assertEqual(replacement.config()['id'],config['id'])
        self.assertEqual(len(replacement.snapshots()),1)
        with self.assertRaises(ValueError):replacement.restore(replacement.snapshots()[0]['id'],self.repository)

    def test_concurrent_operation_is_rejected(self):
        with self.backup.lock():
            with self.assertRaises(RuntimeError):
                with self.backup.lock():pass

if __name__=='__main__':unittest.main()
