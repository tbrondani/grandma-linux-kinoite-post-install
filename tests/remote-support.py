#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Guest test of RustDesk lifecycle through KWin; never injects input events."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import time
import dbus

root=Path(__file__).resolve().parent.parent
for line in subprocess.run(['systemctl','--user','show-environment'],check=True,capture_output=True,text=True).stdout.splitlines():
    if '=' in line:
        key,value=line.split('=',1);parts=shlex.split(value)
        os.environ[key]=parts[0] if len(parts)==1 else value

def active():
    return 'com.rustdesk.RustDesk' in subprocess.run(['flatpak','ps','--columns=application'],capture_output=True,text=True,check=True).stdout.splitlines()

if active():raise SystemExit('Close any existing RustDesk session before running this test.')
bus=dbus.SessionBus()
manager=dbus.Interface(bus.get_object('org.kde.KWin','/Scripting'),'org.kde.kwin.Scripting')
plugin=f'grandma-test-support-{os.getpid()}'
results={}
(root/'test-results').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=os.environ['XDG_RUNTIME_DIR']) as folder, (root/'test-results/remote-support.log').open('w') as log:
    process=subprocess.Popen(['python3',str(Path.home()/'.local/libexec/grandma-linux/remote-support-session.py')],stdout=log,stderr=log)
    def window_action(action):
        path=Path(folder)/'action.js'
        path.write_text('var ws=workspace.windowList();for(var i=0;i<ws.length;i++){if(ws[i].normalWindow && String(ws[i].resourceClass).toLowerCase().indexOf("rustdesk")>=0){'+action+';break;}}')
        sid=int(bus.call_blocking('org.kde.KWin','/Scripting','org.kde.kwin.Scripting','loadScript','ss',(str(path),plugin)))
        try:dbus.Interface(bus.get_object('org.kde.KWin',f'/Scripting/Script{sid}'),'org.kde.kwin.Script').run()
        finally:manager.unloadScript(plugin)
    try:
        time.sleep(8)
        results['started']=process.poll() is None and active()
        window_action('ws[i].minimized=true')
        time.sleep(2)
        results['minimize_keeps_session']=process.poll() is None and active()
        window_action('ws[i].minimized=false;ws[i].closeWindow()')
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:pass
        results['close_stops_session']=process.poll()==0 and not active()
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
        subprocess.run(['flatpak','kill','com.rustdesk.RustDesk'],capture_output=True)
(root/'test-results/remote-support.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
raise SystemExit(0 if all(results.values()) else 1)
