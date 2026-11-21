#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise real Omnidict lookups in a sandbox without network access."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent.parent
base=Path.home()/'.var/app/com.ktechpit.omnidict/data/ktechpit/omnidict/dictionaries'
words={'pt':'casa','en':'house','de':'Haus','fr':'maison','it':'casa','es':'casa'}
results=[]
for package in json.loads((root/'data/dictionaries.json').read_text()):
    db=base/package['dict_id']/package['version']/'dict.sqlite'
    word=words[package['source_lang']]
    result=subprocess.run(['flatpak','run','--unshare=network','com.ktechpit.omnidict','--lookup',str(db),word],capture_output=True,text=True,timeout=30)
    item={'dictionary':package['dict_id'],'word':word,'passed':result.returncode==0 and bool(result.stdout.strip()),'output':result.stdout.strip(),'error':result.stderr.strip() if result.returncode else ''}
    results.append(item);print(json.dumps(item,ensure_ascii=False),flush=True)
(root/'test-results').mkdir(exist_ok=True)
(root/'test-results/offline-dictionaries.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(0 if all(item['passed'] for item in results) else 1)
