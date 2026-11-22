#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check stable GitHub releases and apply verified project updates without Git."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY='tbrondani/grandma-linux-kinoite-post-install'
API=f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
STABLE=re.compile(r'v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
LIMIT=64*1024*1024

class UpdateError(RuntimeError):pass

class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,url):
        if urllib.parse.urlparse(url).scheme!='https':raise UpdateError('download')
        return super().redirect_request(request,fp,code,message,headers,url)


def state_dir():return Path.home()/'.local/state/grandma-linux'
def installed_version():
    path=state_dir()/'installation.json'
    if path.is_file():return json.loads(path.read_text()).get('version','development')
    version=Path(__file__).resolve().parent/'VERSION'
    return version.read_text().strip() if version.is_file() else 'development'


def version_tuple(value):
    match=STABLE.fullmatch(value) if isinstance(value,str) else None
    return tuple(map(int,match.groups())) if match else None


def check_release(current=None):
    request=urllib.request.Request(API,headers={'Accept':'application/vnd.github+json','User-Agent':'GrandmaLinux-Updater','X-GitHub-Api-Version':'2022-11-28'})
    try:
        with urllib.request.build_opener(HTTPSRedirects()).open(request,timeout=30) as response:
            payload=response.read(2*1024*1024+1)
        if len(payload)>2*1024*1024:raise UpdateError('release')
        release=json.loads(payload)
    except urllib.error.HTTPError as error:
        if error.code==404:return None
        raise UpdateError('network') from error
    except (OSError,ValueError) as error:raise UpdateError('network') from error
    return validate_release(release,current or installed_version())


def validate_release(release,current):
    if not isinstance(release,dict):raise UpdateError('release')
    tag=release.get('tag_name','')
    version=version_tuple(tag)
    if not version or release.get('draft',False) or release.get('prerelease',False):raise UpdateError('release')
    installed=version_tuple(current)
    if installed is not None and installed>=version:return {'available':False,'tag':tag,'current':current}
    name='grandma-linux-'+tag+'.tar.gz'
    assets=release.get('assets',[])
    if not isinstance(assets,list):raise UpdateError('package')
    asset=next((a for a in assets if isinstance(a,dict) and a.get('name')==name),None)
    expected=f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
    if not asset or asset.get('browser_download_url')!=expected:raise UpdateError('package')
    digest=asset.get('digest','')
    if not isinstance(digest,str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',digest):raise UpdateError('checksum')
    size=asset.get('size')
    if not isinstance(size,int) or isinstance(size,bool) or not 0<size<=LIMIT:raise UpdateError('package')
    return dict(available=True,tag=tag,current=current,url=expected,sha256=digest[7:],size=size)


def extract(archive,destination,tag):
    expected='grandma-linux-'+tag
    with tarfile.open(archive,'r:gz') as tar:
        members=tar.getmembers();total=0;names=set()
        for member in members:
            path=PurePosixPath(member.name)
            if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0]!=expected:
                raise UpdateError('package')
            if not (member.isfile() or member.isdir()) or member.name in names:raise UpdateError('package')
            total+=member.size;names.add(member.name)
            if total>256*1024*1024:raise UpdateError('package')
        tar.extractall(destination,filter='data')
    root=destination/expected
    if not (root/'setup.sh').is_file() or not (root/'VERSION').is_file():raise UpdateError('package')
    if (root/'VERSION').read_text().strip()!=tag.removeprefix('v'):raise UpdateError('package')
    return root


def download(release,path,progress=None):
    digest=hashlib.sha256();size=0
    request=urllib.request.Request(release['url'],headers={'User-Agent':'GrandmaLinux-Updater'})
    try:
        with urllib.request.build_opener(HTTPSRedirects()).open(request,timeout=90) as response,path.open('wb') as output:
            while block:=response.read(1024*1024):
                size+=len(block)
                if size>release['size']:raise UpdateError('checksum')
                digest.update(block);output.write(block)
                if progress:progress('download',int(size*100/release['size']))
    except (OSError,urllib.error.URLError) as error:raise UpdateError('download') from error
    if size!=release['size'] or digest.hexdigest()!=release['sha256']:raise UpdateError('checksum')


def record_install(root):
    version=(root/'VERSION').read_text().strip()
    if version_tuple(version) is None and not (version.endswith('-dev') and version_tuple(version[:-4]) is not None):raise UpdateError('release')
    path=state_dir()/'installation.json';path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.partial')
    temporary.write_text(json.dumps(dict(version=version,installed_at=datetime.now(timezone.utc).isoformat(),repository=REPOSITORY,revision=(root/'SOURCE_REVISION').read_text().strip() if (root/'SOURCE_REVISION').is_file() else None),indent=2)+'\n')
    temporary.replace(path)


def private_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.partial');temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.chmod(0o600);temporary.replace(path)


def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def pending_path():return state_dir()/'pending-update.json'
def archive_path():return state_dir()/'update-package.tar.gz'


def candidate(release):
    """Check a saved descriptor as strictly as a new GitHub release."""
    try:
        tag=release['tag'];name='grandma-linux-'+tag+'.tar.gz'
        return validate_release(dict(tag_name=tag,assets=[dict(name=name,size=release['size'],
            digest='sha256:'+release['sha256'],browser_download_url=release['url'])]),installed_version())
    except (TypeError,KeyError) as error:raise UpdateError('release') from error


def pending_update():
    if not pending_path().is_file():return None
    try:
        pending=json.loads(pending_path().read_text())
        checked=candidate(pending['release'])
        return dict(release=checked,phase=pending.get('phase','ready'),boot_id=pending.get('boot_id'))
    except (OSError,ValueError,KeyError,TypeError) as error:raise UpdateError('pending') from error


def clear_pending():
    pending_path().unlink(missing_ok=True);archive_path().unlink(missing_ok=True)


def discard_pending():
    directory=state_dir();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (directory/'project-update.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise UpdateError('busy') from error
        clear_pending()


def _apply(release=None,language='en',progress=None):
    directory=state_dir();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    report=progress or (lambda stage,value=None:None)
    with (directory/'project-update.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise UpdateError('busy') from error
        pending=pending_update()
        if pending is not None:
            release=pending['release']
            if release.get('available') and pending['phase']=='reboot-required' and pending['boot_id']==boot_id():return 75
        elif release is None:
            raise UpdateError('pending')
        else:release=candidate(release)
        if not release.get('available'):
            clear_pending();return 0
        archive=archive_path()
        good_archive=archive.is_file() and archive.stat().st_size==release['size'] and hashlib.sha256(archive.read_bytes()).hexdigest()==release['sha256']
        if not good_archive:
            report('download',0)
            temporary=archive.with_suffix('.partial')
            try:
                download(release,temporary,progress)
                temporary.chmod(0o600);temporary.replace(archive)
            finally:temporary.unlink(missing_ok=True)
        private_json(pending_path(),dict(release=release,phase='ready'))
        log_path=directory/'project-update.log'
        with tempfile.TemporaryDirectory(prefix='grandma-project-update-',dir=directory) as folder,log_path.open('a') as log:
            log_path.chmod(0o600)
            log.write('\nGrandma Linux '+release['tag']+' — '+datetime.now(timezone.utc).isoformat()+'\n');log.flush()
            try:
                report('verify')
                root=extract(archive,Path(folder),release['tag'])
                report('install')
                result=subprocess.run(['bash',str(root/'setup.sh'),'--update','--lang='+language],stdout=log,stderr=subprocess.STDOUT)
            except (OSError,tarfile.TarError,ValueError) as error:raise UpdateError('package') from error
            if result.returncode==75:
                private_json(pending_path(),dict(release=release,phase='reboot-required',boot_id=boot_id()))
                return 75
            if result.returncode:raise UpdateError('install')
            if installed_version()!=release['tag'].removeprefix('v'):raise UpdateError('install')
        clear_pending();report('complete')
    return 0


def apply(release=None,language='en',progress=None):
    try:return _apply(release,language,progress)
    except UpdateError as error:
        if str(error)!='busy':
            try:
                path=state_dir()/'project-update.log';path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with path.open('a') as log:
                    path.chmod(0o600);log.write('FAILED '+datetime.now(timezone.utc).isoformat()+': '+str(error)+'\n')
            except OSError:pass
        raise


def available_update():
    pending=pending_update()
    if pending and not pending['release']['available']:
        # Recover if the previous process finished setup but exited before cleanup.
        apply()
        pending=None
    return (pending['release'],True) if pending else (check_release(),False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--record-install',type=Path)
    actions.add_argument('--apply',action='store_true',help='Check and install the latest stable release, or resume a pending update.')
    actions.add_argument('--discard-pending',action='store_true',help='Discard the saved update package; keep installed applications and settings.')
    actions.add_argument('--check',action='store_true',help='Show the current version and available update.')
    parser.add_argument('--lang',choices=['en','pt-BR'],default='en')
    parser.add_argument('--yes',action='store_true',help='Confirm installation without a prompt.')
    parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    pt=args.lang=='pt-BR'
    try:
        if args.record_install:
            if args.dry_run:print('Record the installed Grandma Linux version after successful setup.')
            else:record_install(args.record_install)
            return 0
        if args.discard_pending:
            if not args.dry_run and (args.yes or input('Discard the saved update? [y/N] ').lower() in {'y','yes','s','sim'}):discard_pending()
            return 0
        release,pending=available_update()
        if not args.apply or args.dry_run:
            print(json.dumps(dict(current=installed_version(),pending=bool(pending),release=release),indent=2));return 0
        if release is None:
            print('Ainda não há uma versão estável publicada.' if pt else 'No stable release is published yet.');return 0
        if not release['available']:
            print('Grandma Linux está atualizado.' if pt else 'Grandma Linux is up to date.');return 0
        if not args.yes:
            answer=input(('Instalar ' if pt else 'Install ')+release['tag']+'? [y/N] ')
            if answer.lower() not in {'y','yes','s','sim'}:return 0
        code=apply(release,args.lang,lambda stage,value=None:print(stage+((' '+str(value)+'%') if value is not None else ''),flush=True))
        print(('Reinicie e execute este comando novamente.' if pt else 'Restart and run this command again.') if code==75 else ('Atualização concluída.' if pt else 'Update complete.'))
        return code
    except (EOFError,KeyboardInterrupt):return 130
    except UpdateError as error:
        print(('Não foi possível atualizar: ' if pt else 'Update failed: ')+str(error))
        print(str(state_dir()/'project-update.log'));return 1


if __name__=='__main__':raise SystemExit(main())
