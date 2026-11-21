#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('vm_login',Path(__file__).resolve().parents[1]/'scripts/vm/configure-login.py')
login=importlib.util.module_from_spec(spec);spec.loader.exec_module(login)

class Login(unittest.TestCase):
    def test_both_managers_receive_the_real_wayland_session(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);session=root/'usr/share/wayland-sessions/plasma.desktop'
            session.parent.mkdir(parents=True);session.write_text('[Desktop Entry]\n')
            primary=root/'etc/plasmalogin.conf';primary.parent.mkdir();primary.write_text('# Keep existing settings\n')
            login.configure('maria',root);login.configure('maria',root)
            for relative in ['etc/sddm.conf.d/grandma-test.conf','etc/plasmalogin.conf.d/zz-grandma-test.conf']:
                content=(root/relative).read_text()
                self.assertIn('User=maria\n',content)
                self.assertIn('Session=plasma.desktop\n',content)
                self.assertIn('Relogin=false\n',content)
            self.assertEqual(primary.read_text(),'# Keep existing settings\n')

    def test_missing_session_or_invalid_user_does_not_write_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError):login.configure('maria\nUser=root',root)
            with self.assertRaises(RuntimeError):login.configure('maria',root)
            self.assertFalse((root/'etc').exists())

if __name__=='__main__':unittest.main()
