#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Local restic backups with tagged retention and non-destructive restores."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import uuid

TAG_PREFIX='grandma-linux-'


def private_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:json.dump(data,stream,indent=2);stream.write('\n')
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


class Backup:
    def __init__(self, home=None, config_dir=None, state_dir=None):
        self.home=Path(home or Path.home()).resolve()
        self.config_dir=Path(config_dir or self.home/'.config/grandma-linux')
        self.state_dir=Path(state_dir or self.home/'.local/state/grandma-linux')
        self.config_path=self.config_dir/'backup.json'
        self.status_path=self.state_dir/'backup-status.json'

    @contextmanager
    def lock(self):
        self.state_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
        with (self.state_dir/'backup.lock').open('a') as stream:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise RuntimeError('Another backup or restore is running.')
            yield

    def sources(self):
        paths=[]
        for kind in ['DESKTOP','DOCUMENTS','DOWNLOAD','PICTURES']:
            path=Path(subprocess.check_output(['xdg-user-dir',kind],text=True).strip())
            if not path.is_absolute() or path.resolve()==self.home:
                raise ValueError('Configure the personal folders before enabling backup.')
            path=path.resolve()
            if not path.is_relative_to(self.home):raise ValueError('Backup folders must be inside the user home.')
            if path.is_dir() and path not in paths:paths.append(path)
        if not paths:raise ValueError('No personal folders are available.')
        return paths

    def config(self):
        return json.loads(self.config_path.read_text())

    def validate(self, config):
        root=Path(config['root'])
        if not root.is_absolute() or root.is_symlink():raise ValueError('Invalid backup location.')
        for source in map(Path,config['sources']):
            if root.is_relative_to(source) or source.is_relative_to(root):
                raise ValueError('Backup storage must be outside the folders being copied.')
        marker=root/'grandma-backup.json'
        if not marker.is_file() or json.loads(marker.read_text())['id']!=config['id']:
            raise ValueError('The backup folder is unavailable or belongs to another backup.')
        if not (root/'repository/config').is_file() or not (root/'recovery-key.txt').is_file():
            raise ValueError('The backup repository or recovery key is unavailable.')

    def restic(self, config, *args):
        # Credentials never appear in process arguments or logs.
        root=Path(config['root'])
        env=dict(os.environ,RESTIC_REPOSITORY=str(root/'repository'),RESTIC_PASSWORD_FILE=str(root/'recovery-key.txt'))
        # Do not inherit an unrelated caller's restic backend/password settings.
        for key in ['RESTIC_PASSWORD','RESTIC_PASSWORD_COMMAND','RESTIC_REPOSITORY_FILE']:
            env.pop(key,None)
        result=subprocess.run(['restic',*args],env=env,capture_output=True,text=True)
        if result.returncode:
            raise RuntimeError(f'Restic {args[0]} failed (exit {result.returncode}). '+result.stderr[-1500:])
        return result.stdout

    def configure_local(self, root=None):
        with self.lock():
            if self.config_path.exists():
                config=self.config();self.validate(config);return config
            sources=self.sources()
            root=Path(root or self.home/'.local/share/grandma-linux/backups/local').expanduser().absolute()
            # Resolve ancestors before creating anything, including symlinked user directories.
            root=root.resolve()
            for source in sources:
                if root.is_relative_to(source) or source.is_relative_to(root):
                    raise ValueError('Backup storage must be outside the folders being copied.')
            marker=root/'grandma-backup.json'
            if root.exists() and any(root.iterdir()) and not marker.is_file():
                raise ValueError('The selected folder is not an existing Grandma Linux backup.')
            root.mkdir(parents=True,exist_ok=True,mode=0o700)
            if marker.is_file():
                identity=json.loads(marker.read_text())['id']
                config=dict(root=str(root),sources=list(map(str,sources)),id=identity)
                self.validate(config)
                self.restic(config,'snapshots','--json')
            else:
                identity=uuid.uuid4().hex
                # Initialize in a staging directory. A failed init leaves the
                # requested destination empty and can be retried safely.
                with tempfile.TemporaryDirectory(prefix='.grandma-backup-',dir=root.parent) as staging:
                    staged=Path(staging)
                    key=staged/'recovery-key.txt'
                    fd=os.open(key,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                    with os.fdopen(fd,'w') as stream:stream.write(secrets.token_urlsafe(48)+'\n')
                    candidate=dict(root=str(staged),sources=list(map(str,sources)),id=identity)
                    self.restic(candidate,'init')
                    private_json(staged/'grandma-backup.json',dict(id=identity,format=1))
                    root.rmdir()  # Refuse if another process put files here.
                    staged.replace(root)
                config=dict(root=str(root),sources=list(map(str,sources)),id=identity)
            private_json(self.config_path,config)
            (root/'RECOVERY.txt').write_text(
                'Grandma Linux file backup / Cópia dos arquivos pessoais\n\n'
                'Keep this entire folder, including repository and recovery-key.txt.\n'
                'Guarde esta pasta inteira, incluindo repository e recovery-key.txt.\n'
                'Anyone with both can read this backup. / Quem tiver ambos pode ler esta cópia.\n\n'
                'After reinstall: run Grandma Linux setup, then Recover Files and choose this folder.\n'
                'Após reinstalar: execute a configuração Grandma Linux e abra Recuperar arquivos.\n'
                'A copy on the same disk must be preserved during reinstall; it does not survive formatting that disk.\n'
                'Preserve esta pasta ao reinstalar. Formatar o disco também apaga a cópia.\n'
                'This contains personal files, not a bootable system image.\n'
                'Esta cópia contém arquivos pessoais, não uma imagem inicializável do sistema.\n')
            return config

    def tag(self, config):return TAG_PREFIX+config['id']

    def record(self, **values):
        old=json.loads(self.status_path.read_text()) if self.status_path.exists() else {}
        old.update(values);private_json(self.status_path,old)

    def run(self):
        with self.lock():
            try:
                config=self.config();self.validate(config)
                # Recheck current localized folders on every run. Never back up the repository itself.
                sources=self.sources();check=dict(config,sources=list(map(str,sources)));self.validate(check)
                output=self.restic(config,'backup','--json','--tag',self.tag(config),'--',*map(str,sources))
                summary=next((json.loads(line) for line in reversed(output.splitlines()) if json.loads(line).get('message_type')=='summary'),{})
                self.restic(config,'forget','--tag',self.tag(config),'--group-by','paths','--keep-last','1',
                            '--keep-monthly','12','--keep-yearly','3','--prune')
                self.restic(config,'check')
                self.record(last_success=datetime.now(timezone.utc).isoformat(),error=None,summary=summary)
            except Exception as error:
                self.record(last_attempt=datetime.now(timezone.utc).isoformat(),error=str(error));raise

    def snapshots(self):
        config=self.config();self.validate(config)
        return json.loads(self.restic(config,'snapshots','--json','--tag',self.tag(config)))

    def restore(self, snapshot, parent):
        with self.lock():
            config=self.config();self.validate(config)
            # Only restore a selected snapshot owned by this integration.
            selected=next((s for s in self.snapshots() if s['id']==snapshot),None)
            if selected is None:raise ValueError('Unknown backup version.')
            parent=Path(parent).resolve(strict=True)
            if not parent.is_dir() or parent.is_relative_to(Path(config['root'])):
                raise ValueError('Choose a recovery folder outside the backup repository.')
            destination=Path(tempfile.mkdtemp(prefix='GrandmaLinux-Recovered-',dir=parent))
            # Restore the common user-folder subtree, without /var/home/name
            # wrappers, so Documents and Pictures are immediately visible.
            base=os.path.commonpath([str(Path(p).parent) for p in selected['paths']])
            try:self.restic(config,'restore',snapshot+':'+base,'--target',str(destination),'--overwrite','never','--verify')
            except Exception as error:raise RuntimeError(f'Restore incomplete: {destination}. {error}')
            return destination
