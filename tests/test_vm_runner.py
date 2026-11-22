#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise durable deployment logs and exit codes without running a real VM."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Runner(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'scripts/vm').mkdir(parents=True);(self.root/'tests').mkdir();(self.root/'bin').mkdir()
        for name in ['run-guest.py','start-test.sh']:shutil.copyfile(ROOT/'scripts/vm'/name,self.root/'scripts/vm'/name)
        self.env=dict(os.environ,PATH=str(self.root/'bin')+':'+os.environ['PATH'])
        self.command('gdbus','exit 0')
        self.command('systemctl',"printf 'XDG_SESSION_TYPE=wayland\\nXDG_CURRENT_DESKTOP=KDE\\n'")
        self.command('rpm-ostree',"printf '%s\\n' '{\"deployments\":[{\"booted\":true}]}'")
        (self.root/'setup.sh').write_text("printf 'setup stdout\\n'\nprintf 'setup stderr\\n' >&2\nexit 0\n")
        (self.root/'tests/validate.py').write_text("print('{\"checks\":[]}')\n")
    def tearDown(self):self.temp.cleanup()
    def command(self,name,content):
        path=self.root/'bin'/name;path.write_text('#!/bin/bash\n'+content+'\n');path.chmod(0o755)
    def run_guest(self):return subprocess.run([sys.executable,str(self.root/'scripts/vm/run-guest.py')],env=self.env,capture_output=True,text=True)

    def test_success_captures_both_streams_and_result(self):
        result=self.run_guest();self.assertEqual(result.returncode,0,result.stderr)
        log=(self.root/'setup.log').read_text()
        self.assertIn('setup stdout',log);self.assertIn('setup stderr',log)
        report=json.loads((self.root/'execution.json').read_text())
        self.assertEqual(report['status'],'passed');self.assertEqual(report['setup_exit_code'],0);self.assertEqual(report['validation_exit_code'],0)
        self.assertEqual((self.root/'setup.log').stat().st_mode&0o777,0o600)

    def test_failed_setup_is_not_masked_by_successful_validation(self):
        (self.root/'setup.sh').write_text('echo failure >&2\nexit 3\n')
        result=self.run_guest();self.assertEqual(result.returncode,3)
        report=json.loads((self.root/'execution.json').read_text())
        self.assertEqual(report['status'],'failed');self.assertEqual(report['setup_exit_code'],3)

    def test_log_survives_a_reboot_boundary(self):
        self.command('rpm-ostree',"printf '%s\\n' '{\"deployments\":[{\"booted\":false}]}'")
        self.assertEqual(self.run_guest().returncode,75)
        self.assertTrue(json.loads((self.root/'execution.json').read_text())['reboot_required'])
        self.command('rpm-ostree',"printf '%s\\n' '{\"deployments\":[{\"booted\":true}]}'")
        self.assertEqual(self.run_guest().returncode,0)
        self.assertEqual((self.root/'setup.log').read_text().count('Guest test started:'),2)

    def test_profile_installer_reboot_code_is_not_reported_as_failure(self):
        (self.root/'setup.sh').write_text('exit 75\n')
        result=self.run_guest();self.assertEqual(result.returncode,75)
        report=json.loads((self.root/'execution.json').read_text())
        self.assertEqual(report['status'],'reboot-required');self.assertTrue(report['reboot_required'])
        self.assertFalse((self.root/'validation-report.json').exists())

    def test_host_uses_one_sudo_process_and_does_not_start_a_second_gui(self):
        import shlex
        counter=self.root/'sudo-calls'
        self.command('virsh','exit 0')
        self.command('ssh','exit 88')
        self.command('virt-manager','echo unexpected-viewer >&2; exit 91')
        self.command('sudo','echo call >> '+shlex.quote(str(counter))+'\n'+
                     """while [[ $# -gt 0 ]]; do
if [[ $1 == --report ]]; then
printf '%s\n' '{"host":"127.0.0.1","display":""}' > "$2"
exit 0
fi
shift
done
exit 2""")
        self.command('python3','if [[ $1 == - && ${2:-} == 127.0.0.1 ]]; then exit 0; fi\nexec '+shlex.quote(sys.executable)+' "$@"')
        result=subprocess.run(['bash',str(self.root/'scripts/vm/start-test.sh')],env=dict(self.env,OPEN_VM_DISPLAY='0'),capture_output=True,text=True)
        self.assertEqual(result.returncode,88,result.stdout+result.stderr)
        self.assertEqual(counter.read_text().splitlines(),['call'])
        self.assertNotIn('unexpected-viewer',result.stderr)

    def test_host_preflight_failure_still_writes_log_and_exit_status(self):
        result=subprocess.run(['bash',str(self.root/'scripts/vm/start-test.sh')],env=dict(self.env,VM_USER='Invalid!'),capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stderr)
        reports=list((self.root/'test-results').glob('deploy-*.json'))
        self.assertEqual(len(reports),1)
        report=json.loads(reports[0].read_text())
        self.assertEqual(report['phase'],'preflight');self.assertEqual(report['exit_code'],2);self.assertEqual(report['status'],'failed')
        self.assertIn('Set VM_USER',Path(report['log']).read_text())

if __name__=='__main__':unittest.main()
