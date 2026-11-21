#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run setup in the desktop environment and keep durable logs and exit codes."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[2]
log_path = root / 'setup.log'
log = log_path.open('a', buffering=1)
log_path.chmod(0o600)
result = dict(status='running', started_at=datetime.now(timezone.utc).isoformat(), phase='desktop-session',
              setup_exit_code=None, validation_exit_code=None, reboot_required=False)

def save_result():
    (root / 'execution.json').write_text(json.dumps(result, indent=2) + '\n')

def progress(message):
    print(message, flush=True)
    log.write(message + '\n')

save_result()
progress('Guest test started: ' + result['started_at'])
env = os.environ.copy()
env['GRANDMA_TEST_VM'] = '1'
for attempt in range(120):
    environment = subprocess.run(['systemctl', '--user', 'show-environment'], capture_output=True, text=True)
    if environment.returncode == 0:
        for line in environment.stdout.splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                parsed = shlex.split(value)
                env[key] = parsed[0] if len(parsed) == 1 else value
    if env.get('XDG_SESSION_TYPE') == 'wayland' and 'KDE' in env.get('XDG_CURRENT_DESKTOP', ''):
        break
    if attempt % 10 == 0:
        progress('Waiting for the KDE Wayland desktop session...')
    time.sleep(2)
else:
    result.update(status='failed', phase='desktop-session-failed', finished_at=datetime.now(timezone.utc).isoformat())
    save_result()
    sys.exit('Log into the KDE Wayland desktop in the VM before running this test.')
result['phase'] = 'setup'
save_result()
with subprocess.Popen(['bash', str(root / 'setup.sh'), '--lang=pt-BR'], env=env,
                      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as setup:
    for line in setup.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        log.write(line)
    setup.wait()
result['setup_exit_code'] = setup.returncode
status = subprocess.run(['rpm-ostree', 'status', '--json'], check=True, capture_output=True, text=True)
deployments = json.loads(status.stdout)['deployments']
if setup.returncode == 0 and deployments and not deployments[0].get('booted', False):
    result.update(status='reboot-required', phase='reboot-required', reboot_required=True, finished_at=datetime.now(timezone.utc).isoformat())
    save_result()
    sys.exit(75)
result['phase'] = 'validation'
save_result()
with (root / 'validation-report.json').open('w') as report:
    validation = subprocess.run(['python3', str(root / 'tests/validate.py')], env=env,
                                stdout=report, stderr=log)
result.update(status='passed' if setup.returncode == 0 and validation.returncode == 0 else 'failed',
              phase='finished', validation_exit_code=validation.returncode,
              finished_at=datetime.now(timezone.utc).isoformat())
save_result()
sys.exit(setup.returncode or validation.returncode)
