#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read only the new-VM preferences; never change a domain or account."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from profiles import DEFAULT,merge,read,validate
root=Path(__file__).resolve().parents[2]
raw=read(Path(sys.argv[1]));profile=validate(merge(DEFAULT,raw),root)
print(profile['vm']['username'])
print('1' if profile['vm']['autologin'] else '0')
print('en_US.UTF-8' if raw.get('language','pt-BR')=='en' else 'pt_BR.UTF-8')
