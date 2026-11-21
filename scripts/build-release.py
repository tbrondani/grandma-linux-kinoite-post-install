#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build an update package from tracked files in a clean checkout."""
import argparse
import hashlib
import io
from pathlib import Path
import subprocess
import tarfile
from project_update import version_tuple


def build(root,tag,destination):
    if version_tuple(tag) is None:raise ValueError('Use a stable version, for example v0.1.0')
    if subprocess.check_output(['git','status','--porcelain'],cwd=root):raise ValueError('Use a clean checkout')
    paths=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
    destination.mkdir(parents=True,exist_ok=True)
    archive=destination/('grandma-linux-'+tag+'.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for name in filter(None,paths):
            path=root/name
            if path.is_symlink():raise ValueError('Release source must not contain symbolic links')
            member=tar.gettarinfo(str(path),arcname='grandma-linux-'+tag+'/'+name)
            member.uid=member.gid=0;member.uname=member.gname='';member.mtime=0
            data=(tag.removeprefix('v')+'\n').encode() if name=='VERSION' else path.read_bytes()
            member.size=len(data);tar.addfile(member,io.BytesIO(data))
    archive.with_suffix(archive.suffix+'.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
    return archive

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('tag');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    print(build(Path(__file__).resolve().parents[1],args.tag,args.output))
