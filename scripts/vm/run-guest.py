#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run setup in the logged-in desktop user's environment, then validate."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
env = os.environ.copy()
env['GRANDMA_TEST_VM'] = '1'
# SSH can start before the desktop has imported its environment after reboot.
for attempt in range(120):
    result = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                parsed = shlex.split(value)
                env[key] = parsed[0] if len(parsed) == 1 else value
    if env.get('XDG_SESSION_TYPE') == 'wayland' and 'KDE' in env.get('XDG_CURRENT_DESKTOP', ''):
        break
    if attempt % 10 == 0:
        print('Waiting for the KDE Wayland desktop session...', flush=True)
    time.sleep(2)
else:
    sys.exit('Log into the KDE Wayland desktop in the VM before running this test.')
setup = subprocess.run(['bash', str(root / 'setup.sh'), '--lang=pt-BR'], env=env)
status = subprocess.run(['rpm-ostree', 'status', '--json'], check=True, capture_output=True, text=True)
deployments = json.loads(status.stdout)['deployments']
if setup.returncode == 0 and deployments and not deployments[0].get('booted', False):
    sys.exit(75)
with (root / 'validation-report.json').open('w') as report:
    result = subprocess.run(['python3', str(root / 'tests/validate.py')], env=env, stdout=report)
sys.exit(setup.returncode or result.returncode)
