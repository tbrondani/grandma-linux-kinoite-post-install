#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check that release packages identify a clean source revision and version."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from project_update import extract
spec=importlib.util.spec_from_file_location('build_release',Path(__file__).resolve().parents[1]/'scripts/build-release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class Release(unittest.TestCase):
    def test_clean_package_version_revision_and_dirty_checkout_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);root=folder/'source';root.mkdir()
            for name,data in [('VERSION','0.1.0-dev\n'),('setup.sh','#!/bin/bash\nexit 0\n'),('LICENSE','MIT\n')]:
                (root/name).write_text(data)
            subprocess.run(['git','init','-q',str(root)],check=True)
            subprocess.run(['git','add','.'],cwd=root,check=True)
            subprocess.run(['git','-c','user.name=Release Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],cwd=root,check=True)
            archive=release.build(root,'v0.1.0',folder/'output')
            extracted=extract(archive,folder/'extracted','v0.1.0')
            self.assertEqual((extracted/'VERSION').read_text(),'0.1.0\n')
            revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
            self.assertEqual((extracted/'SOURCE_REVISION').read_text().strip(),revision)
            self.assertTrue(archive.with_suffix('.gz.sha256').is_file())
            (root/'VERSION').write_text('modified')
            with self.assertRaisesRegex(ValueError,'clean checkout'):release.build(root,'v0.1.1',folder/'other')

if __name__=='__main__':unittest.main()
