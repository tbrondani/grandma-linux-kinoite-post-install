#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import configparser
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).resolve().parent.parent / 'scripts/desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


class Launchers(unittest.TestCase):
    def test_alias_icons_exec_and_repeated_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            data = root / 'data-home'
            native = data / 'applications'
            exports = root / '.local/share/flatpak/exports/share'
            apps = exports / 'applications'
            icons = exports / 'icons/hicolor/128x128/apps'
            for path in (root / 'data', root / 'assets', native, apps, icons):
                path.mkdir(parents=True)
            (root / 'assets/chat.svg').write_text('<svg/>')
            (root / 'data/apps.tsv').write_text('org.kde.kdeconnect|kdeconnect-app|Connect Phone|Conectar Celular\ncom.brave.Browser|brave-browser|Internet|Internet\n')
            (native / 'org.kde.kdeconnect.app.desktop').write_text('[Desktop Entry]\nType=Application\nName=KDE Connect\nExec=kdeconnect-app\nIcon=kdeconnect\n')
            brave = apps / 'com.brave.Browser.desktop'
            brave.write_text('[Desktop Entry]\nType=Application\nName=Brave\nExec=/usr/bin/flatpak run com.brave.Browser %U\nIcon=com.brave.Browser\n')
            (icons / 'com.brave.Browser.png').write_bytes(b'fixture')
            with patch.object(Path, 'home', return_value=root), patch.dict('os.environ', {'XDG_DATA_HOME': str(data)}), patch.object(desktop, 'desktop_dir', return_value=root / 'Desktop'), patch.object(desktop.subprocess, 'run'), patch.object(desktop, 'browser_icon', return_value=str(icons / 'chromium.png')):
                desktop.configure(root)
                first = (root / 'Desktop/grandma-com.brave.Browser.desktop').read_bytes()
                desktop.configure(root)
            self.assertEqual(first, (root / 'Desktop/grandma-com.brave.Browser.desktop').read_bytes())
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(native / 'com.brave.Browser.desktop')
            entry = parser['Desktop Entry']
            self.assertEqual(entry['Exec'], '/usr/bin/flatpak run com.brave.Browser %U')
            self.assertEqual(entry['Icon'], str(icons / 'chromium.png'))
            self.assertEqual(entry['Name[pt_BR]'], 'Internet')
            self.assertTrue((native / 'org.kde.kdeconnect.app.desktop.before-grandma').exists())
            self.assertFalse((native / 'org.kde.kdeconnect.desktop').exists())


if __name__ == '__main__':
    unittest.main()
