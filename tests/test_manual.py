#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from manual import build
ROOT=Path(__file__).resolve().parents[1]

class Scripts(HTMLParser):
    def __init__(self):super().__init__();self.count=0;self.data=[];self.in_data=False
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.count+=1;self.in_data=dict(attrs).get('id')=='manual-data'
    def handle_data(self,data):
        if self.in_data:self.data.append(data)
    def handle_endtag(self,tag):
        if tag=='script':self.in_data=False

class Manual(unittest.TestCase):
    def test_single_file_has_both_languages_and_is_stable_on_repeat(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'manual.html';build(ROOT,path,'pt-BR');before=path.read_bytes();build(ROOT,path,'pt-BR')
            self.assertEqual(path.read_bytes(),before)
            parser=Scripts();parser.feed(path.read_text());data=json.loads(''.join(parser.data))
            self.assertEqual(set(data),{'en','pt-BR'});self.assertEqual(len(data['pt-BR']['topics']),16)
            self.assertIn("connect-src 'none'",path.read_text())
            self.assertNotIn('@@CONTENT@@',path.read_text())

    def test_personal_file_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'manual.html';path.write_text('Personal notes')
            with self.assertRaises(RuntimeError):build(ROOT,path)
            self.assertEqual(path.read_text(),'Personal notes')

    def test_content_cannot_close_the_embedded_json_script(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'data/guides').mkdir(parents=True)
            shutil.copytree(ROOT/'data/manual',root/'data/manual')
            payload='</script><script>alert("not executable")</script>'
            for language in ['en','pt-BR']:
                data={'topics':[{'id':'sample','title':payload}]}
                (root/'data/guides'/f'manual.{language}.json').write_text(json.dumps(data))
            path=build(root,root/'manual.html')
            parser=Scripts();parser.feed(path.read_text())
            self.assertEqual(parser.count,2)
            self.assertEqual(json.loads(''.join(parser.data))['en']['topics'][0]['title'],payload)

if __name__=='__main__':unittest.main()
