#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check scoped host preparation without authenticating or changing a real VM."""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('vm_host',Path(__file__).resolve().parents[1]/'scripts/vm/prepare-host.py')
host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)

class Host(unittest.TestCase):
    def test_prepare_starts_referenced_network_and_domain_then_reports_address(self):
        args=argparse.Namespace(vm='test-vm',user='tester',uri='qemu:///system',fresh=False,host='',iso=None,fedora='45',locale='pt_BR.UTF-8',autologin=True)
        def query(uri,*command):
            responses={'dumpxml':'<domain><devices><interface type="network"><source network="default"/></interface></devices></domain>',
                       'net-info':'Active: no','domstate':'shut off','domifaddr':'vnet0 52:54:00:00:00:01 ipv4 192.168.122.100/24'}
            return responses[command[0]]
        with patch.object(host,'virsh',side_effect=query),patch.object(host.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'spice://127.0.0.1:5900\n','')) as run:
            report=host.prepare(args)
        self.assertEqual(report['host'],'192.168.122.100')
        calls=[call.args[0] for call in run.call_args_list]
        self.assertIn(['virsh','--connect','qemu:///system','net-start','default'],calls)
        self.assertIn(['virsh','--connect','qemu:///system','start','test-vm'],calls)
        self.assertTrue(all(command[0]!='sudo' for command in calls))
    def test_report_owner_is_checked_before_truncating(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'host.json';path.write_text('preserve')
            with patch.dict(os.environ,{'SUDO_UID':str(os.getuid()+1)}):
                with self.assertRaisesRegex(RuntimeError,'owner'):host.write_report(path,{'host':'x'})
            self.assertEqual(path.read_text(),'preserve')
            with patch.dict(os.environ,{'SUDO_UID':str(os.getuid())}):host.write_report(path,{'host':'x'})
            self.assertIn('"host"',path.read_text())
    def test_report_refuses_symbolic_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'personal';target.write_text('preserve')
            path=root/'host.json';path.symlink_to(target)
            with self.assertRaises(OSError):host.write_report(path,{'host':'x'})
            self.assertEqual(target.read_text(),'preserve')

if __name__=='__main__':unittest.main()
