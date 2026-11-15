#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
from settings import write_ini

class Settings(unittest.TestCase):
    def test_new_managed_file_does_not_generate_backup_on_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'task.directory'
            write_ini(path,{'Desktop Entry':{'Name':'Utilities'}})
            before=path.read_bytes()
            write_ini(path,{'Desktop Entry':{'Name':'Utilities'}})
            self.assertEqual(path.read_bytes(),before)
            self.assertEqual(list(Path(folder).iterdir()),[path])

    def test_personal_config_is_backed_up_once_and_unrelated_keys_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'example.ini'
            original='[General]\nPersonal=keep\n'
            path.write_text(original)
            write_ini(path,{'General':{'Added':'yes'}})
            write_ini(path,{'General':{'Added':'yes'}})
            self.assertIn('Personal=keep',path.read_text())
            self.assertEqual(path.with_suffix('.ini.before-grandma').read_text(),original)

if __name__=='__main__':unittest.main()
