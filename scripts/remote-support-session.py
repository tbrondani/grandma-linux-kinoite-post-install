#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Tie a manual RustDesk session to its main KWin window, without input injection."""
import fcntl
import os
from pathlib import Path
import signal
import subprocess
import tempfile

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
lock=(Path(os.environ['XDG_RUNTIME_DIR'])/'grandma-remote-support.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
bus=dbus.SessionBus()
name=f'org.grandmalinux.RemoteSupport.p{os.getpid()}'
owner=dbus.service.BusName(name,bus)
loop=GLib.MainLoop()
seen=False

class Session(dbus.service.Object):
    @dbus.service.method('org.grandmalinux.RemoteSupport',in_signature='',out_signature='')
    def Seen(self):
        global seen
        seen=True
    @dbus.service.method('org.grandmalinux.RemoteSupport',in_signature='',out_signature='')
    def Closed(self):
        loop.quit()

bridge=Session(bus,'/Session')
# If the compositor restarts, stop support rather than leave an unmonitored session.
def compositor_changed(_name, previous, current):
    if previous and previous != current:
        loop.quit()
bus.add_signal_receiver(compositor_changed,signal_name='NameOwnerChanged',
    dbus_interface='org.freedesktop.DBus',arg0='org.kde.KWin')
plugin=f'grandma-remote-support-{os.getpid()}'
scripting=dbus.Interface(bus.get_object('org.kde.KWin','/Scripting'),'org.kde.kwin.Scripting')
script='''
var mainId=null;
function watch(w) {
 if (mainId===null && w.normalWindow && String(w.resourceClass).toLowerCase().indexOf("rustdesk")>=0) {
  mainId=String(w.internalId);
  callDBus("BUS", "/Session", "org.grandmalinux.RemoteSupport", "Seen");
 }
}
workspace.windowAdded.connect(watch);
workspace.windowRemoved.connect(function(w) {
 if (mainId!==null && String(w.internalId)===mainId) {
  callDBus("BUS", "/Session", "org.grandmalinux.RemoteSupport", "Closed");
 }
});
var windows=workspace.windowList();
for (var i=0;i<windows.length;i++) watch(windows[i]);
'''.replace('BUS',name)

with tempfile.TemporaryDirectory(prefix='grandma-support-',dir=os.environ['XDG_RUNTIME_DIR']) as folder:
    path=Path(folder)/'watch.js';path.write_text(script)
    try:
        script_id=int(bus.call_blocking('org.kde.KWin','/Scripting','org.kde.kwin.Scripting','loadScript','ss',(str(path),plugin)))
        if script_id<0:raise RuntimeError('Cannot monitor the support window; refusing to start remote support.')
        dbus.Interface(bus.get_object('org.kde.KWin',f'/Scripting/Script{script_id}'),'org.kde.kwin.Script').run()
        child=subprocess.Popen(['flatpak','run','com.rustdesk.RustDesk'])
        def startup_timeout():
            if not seen:
                print('Remote Support did not create a window.',flush=True);loop.quit()
            return False
        def main_exited():
            if child.poll() is not None:loop.quit();return False
            return True
        GLib.timeout_add_seconds(45,startup_timeout)
        GLib.timeout_add_seconds(1,main_exited)
        for signum in (signal.SIGTERM,signal.SIGINT):signal.signal(signum,lambda *_:loop.quit())
        loop.run()
    finally:
        subprocess.run(['flatpak','kill','com.rustdesk.RustDesk'],capture_output=True)
        try:scripting.unloadScript(plugin)
        except dbus.DBusException:pass

raise SystemExit(0 if seen else 1)
