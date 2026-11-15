#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
import theme

class Downloads(unittest.TestCase):
    def test_cached_pin_avoids_network(self):
        with tempfile.TemporaryDirectory() as folder:
            cache=Path(folder);payload=b'reviewed-package'
            package={'id':1,'sha256':hashlib.sha256(payload).hexdigest()}
            target=cache/f'1-{package["sha256"]}.archive';target.write_bytes(payload)
            with patch.object(theme.urllib.request,'urlopen',side_effect=AssertionError('unexpected network')):
                self.assertEqual(theme.fetch(package,cache),target)

    def test_changed_upstream_is_rejected(self):
        class Response(io.BytesIO):
            url='https://files.example/package'
        xml=b'<ocs><data><content><downloadname1>theme.tar.gz</downloadname1><downloadlink1>https://files.example/package</downloadlink1></content></data></ocs>'
        package={'id':1,'name':'fixture','filename':'theme.tar.gz','sha256':'0'*64}
        with tempfile.TemporaryDirectory() as folder, patch.object(theme.urllib.request,'urlopen',side_effect=[Response(xml),Response(b'changed-upstream')]):
            with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):
                theme.fetch(package,Path(folder))
            self.assertEqual(list(Path(folder).iterdir()),[])

    def test_reviewed_manifest_has_fixed_digests(self):
        packages=json.loads((Path(__file__).resolve().parent.parent/'data/themes.json').read_text())
        self.assertEqual({p['id'] for p in packages},set(theme.DESTINATIONS))
        for package in packages:
            self.assertRegex(package['sha256'],r'^[0-9a-f]{64}$')

if __name__=='__main__':unittest.main()
