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
            login.configure('tester',root);login.configure('tester',root)
            for relative in ['etc/sddm.conf.d/grandma-test.conf','etc/plasmalogin.conf.d/zz-grandma-test.conf']:
                content=(root/relative).read_text()
                self.assertIn('User=tester\n',content)
                self.assertIn('Session=plasma.desktop\n',content)
                self.assertIn('Relogin=false\n',content)
            self.assertEqual(primary.read_text(),'# Keep existing settings\n')

    def test_missing_session_or_invalid_user_does_not_write_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(ValueError):login.configure('tester\nUser=root',root)
            with self.assertRaises(RuntimeError):login.configure('tester',root)
            self.assertFalse((root/'etc').exists())

class Provisioning(unittest.TestCase):
    def test_new_vm_user_language_and_autologin_preferences(self):
        spec=importlib.util.spec_from_file_location('kickstart',Path(__file__).resolve().parents[1]/'scripts/vm/kickstart.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        enabled=module.render('ana','$6$fixture','ssh-ed25519 AAAA fixture',autologin=True)
        self.assertIn('user --name=ana',enabled);self.assertIn('User=ana',enabled)
        disabled=module.render('ana','$6$fixture','ssh-ed25519 AAAA fixture',autologin=False,locale='en_US.UTF-8')
        self.assertNotIn('[Autologin]',disabled);self.assertIn('lang en_US.UTF-8',disabled)
        self.assertIn('systemctl enable sshd',disabled)
        with self.assertRaises(ValueError):module.render('bad;user','$6$fixture','ssh-ed25519 AAAA')

if __name__=='__main__':unittest.main()
