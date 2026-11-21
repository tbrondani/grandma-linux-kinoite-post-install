#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Check stable GitHub releases and apply verified project updates without Git."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
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
    match=STABLE.fullmatch(value)
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
    tag=release.get('tag_name','')
    version=version_tuple(tag)
    if not version or release.get('draft',False) or release.get('prerelease',False):raise UpdateError('release')
    installed=version_tuple(current)
    if installed is not None and installed>=version:return {'available':False,'tag':tag,'current':current}
    name='grandma-linux-'+tag+'.tar.gz'
    asset=next((a for a in release.get('assets',[]) if a.get('name')==name),None)
    expected=f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
    if not asset or asset.get('browser_download_url')!=expected:raise UpdateError('package')
    digest=asset.get('digest','')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}',digest):raise UpdateError('checksum')
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


def download(release,path):
    digest=hashlib.sha256();size=0
    request=urllib.request.Request(release['url'],headers={'User-Agent':'GrandmaLinux-Updater'})
    try:
        with urllib.request.build_opener(HTTPSRedirects()).open(request,timeout=90) as response,path.open('wb') as output:
            while block:=response.read(1024*1024):
                size+=len(block)
                if size>release['size']:raise UpdateError('checksum')
                digest.update(block);output.write(block)
    except OSError as error:raise UpdateError('download') from error
    if size!=release['size'] or digest.hexdigest()!=release['sha256']:raise UpdateError('checksum')


def record_install(root):
    version=(root/'VERSION').read_text().strip()
    if version_tuple(version) is None and version!='0.1.0-dev':raise UpdateError('release')
    path=state_dir()/'installation.json';path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.partial')
    temporary.write_text(json.dumps(dict(version=version,installed_at=datetime.now(timezone.utc).isoformat(),repository=REPOSITORY),indent=2)+'\n')
    temporary.replace(path)


def apply(release,language='en'):
    if not release.get('available'):return 0
    directory=state_dir();directory.mkdir(parents=True,exist_ok=True,mode=0o700)
    with (directory/'project-update.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise UpdateError('busy') from error
        log_path=directory/'project-update.log'
        with tempfile.TemporaryDirectory(prefix='grandma-project-update-',dir=directory) as folder,log_path.open('w') as log:
            log_path.chmod(0o600);staging=Path(folder);archive=staging/'release.tar.gz'
            download(release,archive)
            root=extract(archive,staging,release['tag'])
            result=subprocess.run(['bash',str(root/'setup.sh'),'--update','--lang='+language],stdout=log,stderr=subprocess.STDOUT)
            if result.returncode==75:return 75
            if result.returncode:raise UpdateError('install')
            if installed_version()!=release['tag'].removeprefix('v'):raise UpdateError('install')
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-install',type=Path);parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    if args.record_install:
        if args.dry_run:print('Record the installed Grandma Linux version after successful setup.')
        else:record_install(args.record_install)
    else:print(json.dumps(check_release(),indent=2))
