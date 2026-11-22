#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import io
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import reading

class Reading(unittest.TestCase):
    def test_restore_changes_only_owned_keys_and_keeps_first_original(self):
        with tempfile.TemporaryDirectory() as folder:
            saved=Path(folder)/'original.json'
            original={file+'|'+group+'|'+key:('Noto Sans,10' if key=='font' else None) for file,group,key in reading.KEYS}
            def query(command,**kwargs):
                if command[0]=='fc-match':return reading.FAMILY
                key=command[command.index('--key')+1];return 'Noto Sans,10\n' if key=='font' else reading.MISSING+'\n'
            with patch.object(reading,'original_path',return_value=saved),patch.object(reading.subprocess,'check_output',side_effect=query),patch.object(reading,'write') as write:
                reading.apply('standard');self.assertEqual(json.loads(saved.read_text()),original)
                reading.apply('large');self.assertEqual(json.loads(saved.read_text()),original)
                write.reset_mock();reading.apply('restore')
                self.assertFalse(saved.exists())
                self.assertEqual(len(write.call_args_list),len(reading.KEYS))
                for call,(file,group,key) in zip(write.call_args_list,reading.KEYS):self.assertEqual(call.args,(file,group,key,original[file+'|'+group+'|'+key]))
                write.reset_mock();reading.apply('restore');write.assert_not_called()
    def test_no_original_is_saved_when_font_is_unavailable(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(reading,'original_path',return_value=Path(folder)/'original.json') as original,patch.object(reading.subprocess,'check_output',return_value='fallback'),patch.object(reading,'write') as write:
            with self.assertRaises(RuntimeError):reading.apply('large')
            self.assertFalse(original.return_value.exists());write.assert_not_called()
    def test_modified_personal_font_is_preserved(self):
        root=Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'data/reading-fonts.json').read_text())
        with tempfile.TemporaryDirectory() as folder,patch.dict(reading.os.environ,{'XDG_DATA_HOME':folder}):
            destination=Path(folder)/'fonts/grandma-linux/AtkinsonHyperlegibleNext';destination.mkdir(parents=True)
            target=destination/manifest['files'][0]['filename'];target.write_bytes(b'personal font')
            with patch.object(reading.urllib.request,'urlopen',side_effect=AssertionError('unexpected network')):
                with self.assertRaisesRegex(RuntimeError,'modified font'):reading.install(root)
            self.assertEqual(target.read_bytes(),b'personal font')
    def test_hash_failure_installs_nothing(self):
        class Response(io.BytesIO):url='https://example.com/font'
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder,patch.dict(reading.os.environ,{'XDG_DATA_HOME':folder}),patch.object(reading.urllib.request,'urlopen',return_value=Response(b'bad font')):
            with self.assertRaisesRegex(RuntimeError,'checksum mismatch'):reading.install(root)
            self.assertEqual(list(Path(folder).iterdir()),[])

if __name__=='__main__':unittest.main()
