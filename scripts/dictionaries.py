#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Install pinned, attributed word dictionaries in Omnidict's documented bundle format."""
import argparse
from compression import zstd
import hashlib
from html import escape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import tempfile
import unicodedata
import urllib.request
import zipfile

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self,data): self.parts.append(data)

def normalize(word):
    word=unicodedata.normalize('NFKC',word).casefold()
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD',word) if not unicodedata.combining(c)).split())

def download(package,cache):
    path=cache/f'{package["dict_id"]}-{package["sha256"]}.download'
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==package['sha256']:return path
    with urllib.request.urlopen(package['url'],timeout=90) as response:
        payload=response.read(100*1024*1024+1)
    if len(payload)>100*1024*1024 or hashlib.sha256(payload).hexdigest()!=package['sha256']:
        raise RuntimeError(f'Dictionary checksum mismatch: {package["dict_id"]}')
    cache.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.partial');temporary.write_bytes(payload);temporary.replace(path)
    return path

def convert_stardict(archive,template,destination,package):
    # Read the public schema from an upstream bundle; do not copy application code.
    with sqlite3.connect(f'file:{template}?mode=ro',uri=True) as source, sqlite3.connect(destination) as db:
        names={'meta','entries','pronunciations','senses','examples','forms','relations','fts_map','fts','suggest'}
        for name,sql in source.execute("select name,sql from sqlite_master where type='table'"):
            if name in names:db.execute(sql)
        for sql, in source.execute("select sql from sqlite_master where type='index' and sql is not null"):
            if not any(x in sql for x in ['fts_data','fts_idx','suggest_']):db.execute(sql)
        with zipfile.ZipFile(archive) as z:
            prefix=f'{package["dict_id"]}/'
            info=z.read(prefix+'stardict.ifo').decode()
            if 'sametypesequence=h' not in info or 'idxoffsetbits=64' in info:
                raise RuntimeError('Unsupported StarDict format; source review required.')
            index=z.read(prefix+'stardict.idx');definitions=z.read(prefix+'stardict.dict')
        position=0;count=0
        while position<len(index):
            end=index.index(b'\0',position);word=index[position:end].decode()
            offset,size=struct.unpack('>II',index[end+1:end+9]);position=end+9
            parser=PlainText();parser.feed(definitions[offset:offset+size].decode())
            plain=' '.join(parser.parts);norm=normalize(word);count+=1
            db.execute('insert into entries values(?,?,?,?,?,?,?)',(count,word,norm,package['source_lang'],None,plain[:160],norm.encode()))
            db.execute('insert into senses values(?,?,?,?,?,?,?,?)',(count,count,1,None,None,None,escape(plain),plain))
            db.execute('insert into fts(rowid,headword,definition_plain,example_text) values(?,?,?,?)',(count,word,plain,''))
            db.execute('insert into fts_map values(?,?)',(count,count))
        for word, in db.execute('select distinct headword_norm from entries order by headword_norm').fetchall():
            db.execute('insert into suggest(word) values(?)',('\x02'+word+'\x03',))
        meta={key:str(package[key]) for key in ['dict_id','name','source_lang','target_lang','version','schema_version','publisher','license','license_url','attribution']}
        meta.update(entry_count=str(count),built_at='2026-11-15T00:00:00Z',kind='bilingual',source_url=package['url'])
        db.executemany('insert into meta values(?,?)',meta.items())
        db.execute("insert into fts(fts) values('optimize')");db.commit()

def install(root,dry_run=False):
    packages=json.loads((root/'data/dictionaries.json').read_text())
    if dry_run:
        print('Offline dictionaries: Portuguese ↔ Spanish, French, English, German, Italian.');return
    target=Path.home()/'.var/app/com.ktechpit.omnidict/data/ktechpit/omnidict/dictionaries'
    cache=Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'grandma-linux/dictionaries'
    # Omnidict documents dict-id/version/dict.sqlite as its normal installed bundle layout.
    for package in packages:
        directory=target/package['dict_id']/package['version'];database=directory/'dict.sqlite'
        if database.is_file():
            with sqlite3.connect(f'file:{database}?mode=ro',uri=True) as db:
                meta=dict(db.execute('select key,value from meta'))
                if meta.get('dict_id')==package['dict_id'] and meta.get('version')==package['version']:continue
        archive=download(package,cache)
        directory.mkdir(parents=True,exist_ok=True)
        temporary=database.with_suffix('.partial')
        if temporary.exists():temporary.unlink()
        if package['format']=='odict':
            with zstd.open(archive,'rb') as source,temporary.open('wb') as output:shutil.copyfileobj(source,output)
        else:
            template=next(target.glob('freedict-pt-en/*/dict.sqlite'))
            convert_stardict(archive,template,temporary,package)
        with sqlite3.connect(f'file:{temporary}?mode=ro',uri=True) as db:
            if db.execute('pragma integrity_check').fetchone()[0]!='ok':raise RuntimeError('Invalid dictionary database.')
            meta=dict(db.execute('select key,value from meta'))
            if meta['dict_id']!=package['dict_id']:raise RuntimeError('Dictionary identity mismatch.')
        temporary.replace(database)
        (directory/'SOURCE.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n')
        print(f'Installed offline dictionary: {package["name"]}',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true')
    install(Path(__file__).resolve().parent.parent,parser.parse_args().dry_run)
