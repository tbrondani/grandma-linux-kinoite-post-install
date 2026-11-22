#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import fcntl
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
    def fixture(self,folder):
        source=folder/'source';source.mkdir();(source/'VERSION').write_text('0.1.0')
        update.record_install(source)
        archive=folder/'release.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for name,data in [('VERSION',b'0.2.0\n'),('setup.sh',b'#!/bin/bash\nexit 0\n')]:
                member=tarfile.TarInfo('grandma-linux-v0.2.0/'+name);member.size=len(data);tar.addfile(member,io.BytesIO(data))
        descriptor=update.validate_release(self.release(),'0.1.0')
        descriptor.update(size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        return archive,descriptor

    def test_update_keeps_version_on_failed_install_and_can_retry(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)/'state'):
            folder=Path(directory);archive,release=self.fixture(folder)
            with patch.object(update.urllib.request,'build_opener') as opener,patch.object(update.subprocess,'run') as run:
                opener.return_value.open.side_effect=lambda *args,**kwargs:archive.open('rb')
                run.return_value.returncode=1
                with self.assertRaisesRegex(update.UpdateError,'install'):update.apply(release)
                self.assertEqual(update.installed_version(),'0.1.0');self.assertTrue(update.pending_path().is_file())
                self.assertEqual(update.archive_path().stat().st_mode&0o777,0o600)
                def success(args,**kwargs):
                    update.record_install(Path(args[1]).parent)
                    return type('Result',(),{'returncode':0})()
                run.side_effect=success
                opener.return_value.open.side_effect=AssertionError('Retry must reuse the verified package')
                self.assertEqual(update.apply(),0)
                self.assertEqual(update.installed_version(),'0.2.0');self.assertFalse(update.pending_path().exists())
                self.assertFalse(update.archive_path().exists())

    def test_reboot_resume_uses_same_package_and_requires_new_boot(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)/'state'):
            folder=Path(directory);archive,release=self.fixture(folder)
            with patch.object(update.urllib.request,'build_opener') as opener,patch.object(update.subprocess,'run') as run,patch.object(update,'boot_id',return_value='boot-one') as boot:
                opener.return_value.open.side_effect=lambda *args,**kwargs:archive.open('rb')
                run.return_value.returncode=75
                self.assertEqual(update.apply(release),75)
                self.assertEqual(update.installed_version(),'0.1.0')
                self.assertEqual(update.pending_update()['phase'],'reboot-required')
                run.reset_mock();self.assertEqual(update.apply(),75);run.assert_not_called()
                boot.return_value='boot-two'
                def success(args,**kwargs):
                    update.record_install(Path(args[1]).parent)
                    return type('Result',(),{'returncode':0})()
                run.side_effect=success
                opener.return_value.open.side_effect=AssertionError('Resume must not download again')
                self.assertEqual(update.apply(),0)
                self.assertFalse(update.pending_path().exists());self.assertEqual(update.installed_version(),'0.2.0')

    def test_completed_pending_state_does_not_hide_a_newer_release(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)/'state'):
            archive,descriptor=self.fixture(Path(directory))
            source=Path(directory)/'source';(source/'VERSION').write_text('0.2.0');update.record_install(source)
            update.private_json(update.pending_path(),dict(release=descriptor,phase='reboot-required',boot_id=update.boot_id()))
            update.archive_path().write_bytes(archive.read_bytes())
            with patch.object(update,'check_release',return_value={'available':True,'tag':'v0.3.0'}) as check:
                release,pending=update.available_update()
                self.assertEqual(release['tag'],'v0.3.0');self.assertFalse(pending);check.assert_called_once()
            self.assertFalse(update.pending_path().exists());self.assertFalse(update.archive_path().exists())

    def test_concurrent_update_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)):
            with (Path(directory)/'project-update.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(update.UpdateError,'busy'):update.apply()

    def test_discard_keeps_installed_version_and_history(self):
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)/'state'):
            self.fixture(Path(directory));before=update.installed_version()
            update.private_json(update.pending_path(),{'release':'broken'})
            update.archive_path().write_bytes(b'cached package')
            log=update.state_dir()/'project-update.log';log.write_text('history')
            update.discard_pending()
            self.assertFalse(update.pending_path().exists());self.assertFalse(update.archive_path().exists())
            self.assertEqual(update.installed_version(),before);self.assertEqual(log.read_text(),'history')

    def test_malformed_release_and_saved_download_are_rejected(self):
        for payload in [None,[],{'tag_name':None},{'tag_name':'v0.2.0','assets':None}]:
            with self.assertRaises(update.UpdateError):update.validate_release(payload,'0.1.0')
        with tempfile.TemporaryDirectory() as directory,patch.object(update,'state_dir',return_value=Path(directory)):
            release=self.release();descriptor=update.validate_release(release,'0.1.0');descriptor['url']='file:///tmp/script'
            update.private_json(update.pending_path(),dict(release=descriptor))
            with self.assertRaises(update.UpdateError):update.pending_update()

    def test_update_mode_preserves_removed_shortcuts_and_backup_settings(self):
        import user_tools_setup
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);desktop=home/'Desktop';desktop.mkdir()
            existing=home/'.config/grandma-linux/backup.json';existing.parent.mkdir(parents=True);existing.write_text('{}')
            with patch.object(user_tools_setup.Path,'home',return_value=home),patch.dict(user_tools_setup.os.environ,{'XDG_CONFIG_HOME':str(home/'.config'),'XDG_DATA_HOME':str(home/'.local/share')}),patch.object(user_tools_setup.subprocess,'check_output',return_value=str(desktop)),patch.object(user_tools_setup.subprocess,'run'),patch.object(user_tools_setup,'Backup') as backup:
                user_tools_setup.install(root,update=True)
                backup.assert_not_called()
            self.assertFalse((desktop/'grandma-help.desktop').exists())
            self.assertTrue((home/'.local/libexec/grandma-linux/project_update.py').exists())
            wrapper=home/'.local/bin/grandma-update'
            self.assertTrue(wrapper.read_text().startswith('#!/usr/bin/env python3\n'))
            self.assertEqual(wrapper.stat().st_mode&0o777,0o755)

if __name__=='__main__':unittest.main()
