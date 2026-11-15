#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guest startup checks, not a substitute for visual or feature validation."""
import concurrent.futures
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import time

root=Path(__file__).resolve().parent.parent
env=os.environ.copy()
for line in subprocess.run(['systemctl','--user','show-environment'],check=True,capture_output=True,text=True).stdout.splitlines():
    if '=' in line:
        key,value=line.split('=',1)
        parts=shlex.split(value)
        env[key]=parts[0] if len(parts)==1 else value
if env.get('XDG_SESSION_TYPE')!='wayland':
    raise SystemExit('Run with an active Wayland desktop.')
logs=root/'test-results/app-startup'
logs.mkdir(parents=True,exist_ok=True)
rows=[]
for row in (root/'data/apps.tsv').read_text().splitlines():
    if row and not row.startswith('#'):
        rows.append(row.split('|'))

def probe(row):
    app_id,native,en,pt=row
    scopes=[]
    for scope in ('--user','--system'):
        if subprocess.run(['flatpak','info',scope,app_id],capture_output=True).returncode==0:
            scopes.append(scope)
    if scopes:
        # Do not interrupt apps that the user already opened.
        running=subprocess.run(['flatpak','ps','--columns=application'],capture_output=True,text=True).stdout.splitlines()
        if app_id in running:
            return {'app':app_id,'passed':True,'detail':'Already running; not interrupted.'}
        cmd=['flatpak','run',scopes[0],app_id]
    else:
        if subprocess.run(['pgrep','-x',native],capture_output=True).returncode==0:
            return {'app':app_id,'passed':True,'detail':'Already running; not interrupted.'}
        cmd=[native]
    with (logs/f'{app_id}.log').open('w') as log:
        try:
            process=subprocess.Popen(cmd,env=env,stdout=log,stderr=log,start_new_session=True)
        except OSError as exc:
            return {'app':app_id,'passed':False,'detail':str(exc)}
        time.sleep(6)
        code=process.poll()
        if code is None:
            if scopes:
                subprocess.run(['flatpak','kill',app_id],capture_output=True)
            else:
                os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait()
        return {'app':app_id,'passed':code in (None,0),'detail':f'Launch exit={code}; render and interaction not verified.'}

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=[]
    for result in pool.map(probe,rows):
        results.append(result)
        print(json.dumps(result,ensure_ascii=False),flush=True)
(logs.parent/'app-startup.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(item['passed'] for item in results) else 1)
