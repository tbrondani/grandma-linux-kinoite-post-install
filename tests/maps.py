#!/usr/bin/env python3
"""Check catalogue selection and rejection of corrupted map downloads."""
import base64
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('maps', Path(__file__).resolve().parents[1] / 'scripts/maps.py')
maps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maps)

class MapsTest(unittest.TestCase):
    def test_selection(self):
        leaf = {'id': 'Portugal_Porto', 's': 3}
        tree = {'id': 'Countries', 'g': [{'id': 'Portugal', 'g': [leaf]}]}
        self.assertEqual(maps.select(tree, ['Portugal', 'Portugal_Porto']), [leaf])
        with self.assertRaises(ValueError): maps.select(tree, ['Unknown'])

    def test_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'map.mwm'
            leaf = {'s': 3, 'sha1_base64': base64.b64encode(hashlib.sha1(b'abc').digest()).decode()}
            path.write_bytes(b'abc')
            self.assertTrue(maps.valid(path, leaf))
            path.write_bytes(b'bad')
            self.assertFalse(maps.valid(path, leaf))

    def test_legacy_catalogue_fallback(self):
        catalogue={'v':260527,'g':[]}
        with patch.object(maps.subprocess,'check_output',side_effect=[subprocess.CalledProcessError(1,['cat']),json.dumps(catalogue).encode()]):
            self.assertEqual(maps.read_catalogue(),catalogue)

    def test_modern_catalogue_and_blake3(self):
        catalogue={'v':261110,'g':[]}
        with patch.object(maps.subprocess,'check_output',return_value=json.dumps(catalogue).encode()) as call:
            self.assertEqual(maps.read_catalogue(),catalogue)
            self.assertTrue(call.call_args.args[0][-1].endswith('countries.json'))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'map.mwm';path.write_bytes(b'abc')
            digest=bytes.fromhex('6437b3ac38465133ff')
            leaf={'s':3,'h':base64.b64encode(digest).decode()}
            with patch.object(maps.subprocess,'check_output',return_value=digest.hex()+'\n'):
                self.assertTrue(maps.valid(path,leaf))
            with patch.object(maps.subprocess,'check_output',return_value='000000000000000000\n'):
                self.assertFalse(maps.valid(path,leaf))
            with self.assertRaises(ValueError):maps.valid(path,{'s':3,'h':'YQ=='})

    def test_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'Portugal_Porto.mwm'
            target.write_bytes(b'old')
            leaf = {'id': 'Portugal_Porto', 's': 4, 'sha1_base64': 'invalid'}
            with patch.object(maps.urllib.request, 'urlopen', side_effect=OSError('offline')):
                with self.assertRaises(RuntimeError): maps.download(leaf, '260527', Path(folder), ['https://example.org'])
            self.assertEqual(target.read_bytes(), b'old')
            self.assertFalse(target.with_suffix('.mwm.partial').exists())

if __name__ == '__main__': unittest.main()
