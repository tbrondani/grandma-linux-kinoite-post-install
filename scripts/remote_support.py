#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Set manual remote-support defaults without installing a system service."""
from pathlib import Path
import re

OPTIONS={'verification-method':'use-temporary-password','temporary-password-length':'10',
         'approve-mode':'password','direct-server':'N','enable-lan-discovery':'N'}

def configure():
    root=Path.home()/'.var/app/com.rustdesk.RustDesk/config/rustdesk'
    root.mkdir(parents=True,exist_ok=True)
    path=root/'RustDesk2.toml'
    text=path.read_text() if path.exists() else ''
    lines=text.splitlines(); output=[]; in_options=False; seen=set(); has_options=False
    for line in lines:
        stripped=line.strip()
        if stripped.startswith('['):
            if in_options:
                output.extend(f'{key} = "{value}"' for key,value in OPTIONS.items() if key not in seen)
            in_options=stripped=='[options]';has_options=has_options or in_options
        match=re.match(r'^\s*([\w-]+)\s*=',line) if in_options else None
        if match and match[1] in OPTIONS:
            key=match[1];output.append(f'{key} = "{OPTIONS[key]}"');seen.add(key)
        else:output.append(line)
    if not has_options:output.append('[options]');in_options=True
    if in_options:output.extend(f'{key} = "{value}"' for key,value in OPTIONS.items() if key not in seen)
    content='\n'.join(output)+'\n'
    if content!=text:path.write_text(content)
    autostart=Path.home()/'.config/autostart/rustdesk.desktop'
    autostart.parent.mkdir(parents=True,exist_ok=True)
    autostart.write_text('[Desktop Entry]\nType=Application\nName=RustDesk\nHidden=true\n')
