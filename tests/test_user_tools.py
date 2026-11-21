#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec=importlib.util.spec_from_file_location('user_tools',Path(__file__).resolve().parents[1]/'scripts/user-tools.py')
tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)

class UserTools(unittest.TestCase):
    def test_help_remote_opens_only_the_manual_support_wrapper(self):
        with patch.object(tools,'dialog',return_value='remote'),patch.object(tools.subprocess,'Popen') as launch:
            tools.help_menu(tools.Backup())
        launch.assert_called_once_with([sys.executable,str(tools.BASE/'remote-support-session.py')])

    def test_cancelled_recovery_does_not_run_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            backup=tools.Backup(config_dir=Path(folder)/'config',state_dir=Path(folder)/'state')
            with patch.object(tools,'dialog',side_effect=tools.Cancelled()),patch.object(backup,'restore') as restore:
                with self.assertRaises(tools.Cancelled):tools.recover(backup)
                restore.assert_not_called()

    def test_manual_languages_cover_the_same_tasks_with_short_procedures(self):
        guides=Path(__file__).resolve().parents[1]/'data/guides'
        english=json.loads((guides/'manual.en.json').read_text())
        portuguese=json.loads((guides/'manual.pt-BR.json').read_text())
        ids=[t['id'] for t in english['topics']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(ids,[t['id'] for t in portuguese['topics']])
        for manual in [english,portuguese]:
            for topic in manual['topics']:
                self.assertGreaterEqual(len(topic['steps']),1)
                self.assertLessEqual(len(topic['steps']),5)
                self.assertTrue(topic['result'])
        # A conservative basic word count, not a complete STE dictionary audit.
        for topic in english['topics']:
            for step in topic['steps']:
                self.assertLessEqual(len(step.split()),20,step)

    def test_manual_opens_the_local_desktop_file_without_a_server(self):
        with tempfile.TemporaryDirectory() as folder:
            desktop=Path(folder)/'Área de trabalho';desktop.mkdir()
            manual=desktop/'.grandma-linux-manual.html';manual.write_text('manual')
            with patch.object(tools.subprocess,'check_output',return_value=str(desktop)), \
                 patch.object(tools.shutil,'which',return_value=None), \
                 patch.object(tools.subprocess,'run') as launch:
                tools.guide()
            launch.assert_called_once_with(['xdg-open',manual.as_uri()],check=True)

    def test_manual_uses_an_app_window_with_the_existing_brave_flatpak(self):
        with tempfile.TemporaryDirectory() as folder:
            desktop=Path(folder);manual=desktop/'.grandma-linux-manual.html';manual.write_text('manual')
            with patch.object(tools.subprocess,'check_output',return_value=str(desktop)), \
                 patch.object(tools.shutil,'which',side_effect=lambda name:'/usr/bin/flatpak' if name=='flatpak' else None), \
                 patch.object(tools.subprocess,'run',return_value=subprocess.CompletedProcess([],0)), \
                 patch.object(tools.subprocess,'Popen') as launch:
                tools.guide()
            self.assertIn('--app='+manual.as_uri(),launch.call_args.args[0])
            self.assertEqual(launch.call_args.args[0][:3],['flatpak','run','com.brave.Browser'])

    def test_setup_installs_both_manuals_and_reuses_the_desktop_shortcut(self):
        import user_tools_setup
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder);desktop=home/'Desktop'
            backup=MagicMock()
            backup.config_path=home/'backup.json'
            backup.status_path=home/'status.json'
            backup.status_path.write_text(json.dumps({'last_success':'2026-11-21'}))
            with patch.object(user_tools_setup.Path,'home',return_value=home), \
                 patch.dict(user_tools_setup.os.environ,{'XDG_CONFIG_HOME':str(home/'.config'),'XDG_DATA_HOME':str(home/'.local/share')}), \
                 patch.object(user_tools_setup,'Backup',return_value=backup), \
                 patch.object(user_tools_setup.subprocess,'check_output',return_value=str(desktop)), \
                 patch.object(user_tools_setup.subprocess,'run'):
                user_tools_setup.install(root)
                user_tools_setup.install(root)
            for language in ['en','pt-BR']:
                installed=home/'.local/libexec/grandma-linux/guides'/f'manual.{language}.json'
                self.assertEqual(installed.read_bytes(),(root/'data/guides'/installed.name).read_bytes())
            shortcuts=list(desktop.glob('grandma-guide*.desktop'))
            self.assertEqual(len(shortcuts),1)
            self.assertIn('Name[pt_BR]=Manual de uso',shortcuts[0].read_text())
            self.assertIn('manual-data',(desktop/'.grandma-linux-manual.html').read_text())
            backup.run.assert_not_called()

    def test_support_report_does_not_include_paths_credentials_or_host_name(self):
        with tempfile.TemporaryDirectory() as folder:
            backup=tools.Backup(config_dir=Path(folder)/'config',state_dir=Path(folder)/'state')
            tools.private_json(backup.config_path,{'root':'/secret-backup-path','password':'secret-password'})
            result=subprocess.CompletedProcess([],0,'com.example.App\t1.0\n','')
            with patch.object(tools,'view'),patch.object(tools.subprocess,'run',return_value=result):
                tools.support_information(backup)
            report=(backup.state_dir/'support-information.txt').read_text()
            self.assertNotIn('secret-backup-path',report)
            self.assertNotIn('secret-password',report)
            self.assertNotIn(tools.platform.node(),report)
            self.assertIn('com.example.App',report)

if __name__=='__main__':unittest.main()
