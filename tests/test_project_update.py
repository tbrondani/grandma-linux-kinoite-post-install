#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import project_update as update

class Updates(unittest.TestCase):
    def release(self):
        tag='v0.2.0';name='grandma-linux-'+tag+'.tar.gz'
        return dict(tag_name=tag,assets=[dict(name=name,size=10,digest='sha256:'+'a'*64,browser_download_url=f'https://github.com/{update.REPOSITORY}/releases/download/{tag}/{name}')])
    def test_only_new_stable_versions(self):
        self.assertTrue(update.validate_release(self.release(),'0.1.0')['available'])
        self.assertFalse(update.validate_release(self.release(),'0.2.0')['available'])
        self.assertFalse(update.validate_release(self.release(),'0.3.0')['available'])
        for key in ['draft','prerelease']:
            release=self.release();release[key]=True
            with self.assertRaises(update.UpdateError):update.validate_release(release,'0.1.0')
    def test_requires_own_release_asset_and_digest(self):
        for key,value in [('digest',''),('browser_download_url','https://example.com/package'),('size',True)]:
            release=self.release();release['assets'][0][key]=value
            with self.assertRaises(update.UpdateError):update.validate_release(release,'0.1.0')
    def test_rejects_unsafe_archive_before_writing(self):
        for name,kind in [('../outside',tarfile.REGTYPE),('grandma-linux-v0.2.0/link',tarfile.SYMTYPE)]:
            with tempfile.TemporaryDirectory() as directory:
                folder=Path(directory);archive=folder/'update.tar.gz'
                with tarfile.open(archive,'w:gz') as tar:
                    member=tarfile.TarInfo(name);member.type=kind;member.linkname='/tmp/outside';tar.addfile(member)
                with self.assertRaises(update.UpdateError):update.extract(archive,folder/'output','v0.2.0')
                self.assertFalse((folder/'output').exists())
    def test_checksum_mismatch(self):
        class Response(io.BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        with tempfile.TemporaryDirectory() as directory,patch.object(update.urllib.request,'build_opener') as opener:
            opener.return_value.open.return_value=Response(b'wrong')
            with self.assertRaises(update.UpdateError):update.download(dict(url='https://example.com',size=5,sha256=hashlib.sha256(b'right').hexdigest()),Path(directory)/'archive')
    def test_update_keeps_version_on_failed_install(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);root=folder/'source';root.mkdir();(root/'VERSION').write_text('0.1.0')
            with patch.object(update,'state_dir',return_value=folder/'state'):
                update.record_install(root)
                with patch.object(update,'download'),patch.object(update,'extract',return_value=root),patch.object(update.subprocess,'run') as run:
                    run.return_value.returncode=1
                    with self.assertRaises(update.UpdateError):update.apply(dict(available=True,tag='v0.2.0'))
                self.assertEqual(update.installed_version(),'0.1.0')
    def test_update_mode_preserves_removed_shortcuts_and_backup_settings(self):
        import user_tools_setup
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);desktop=home/'Desktop';desktop.mkdir()
            with patch.object(user_tools_setup.Path,'home',return_value=home),patch.dict(user_tools_setup.os.environ,{'XDG_CONFIG_HOME':str(home/'.config'),'XDG_DATA_HOME':str(home/'.local/share')}),patch.object(user_tools_setup.subprocess,'check_output',return_value=str(desktop)),patch.object(user_tools_setup.subprocess,'run'),patch.object(user_tools_setup,'Backup') as backup:
                user_tools_setup.install(root,update=True)
                backup.assert_not_called()
            self.assertFalse((desktop/'grandma-help.desktop').exists())
            self.assertTrue((home/'.local/libexec/grandma-linux/project_update.py').exists())

if __name__=='__main__':unittest.main()
