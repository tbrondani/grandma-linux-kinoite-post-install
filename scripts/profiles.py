#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Strict portable YAML profiles, selection plans and private operation history."""
from datetime import datetime,timezone
import copy
import pwd
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

FEATURES=dict(accessibility=True,theme=True,offline_maps=True,dictionaries=True,translator=True,games=True,remote_support=True,backup=True,ai=False)
GROUPS={'app.organicmaps.desktop':'offline_maps','com.ktechpit.omnidict':'dictionaries','com.rustdesk.RustDesk':'remote_support'}
GAME_IDS={'org.kde.kpat','org.kde.kmines','org.kde.ksudoku','org.kde.kmahjongg','org.kde.palapeli','org.kde.kblocks','org.kde.kapman'}
CORE={'com.brave.Browser','org.kde.dolphin'}
DEFAULT=dict(schema_version=1,language='en',features=FEATURES,applications={},environment={},system=dict(username=None,home=None),storage=dict(mount_points={}),vm=dict(username='tester',autologin=True))
class ProfileError(ValueError):pass


def profile_path():return Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'grandma-linux/profile.yaml'
def state_dir():return Path.home()/'.local/state/grandma-linux'
def manifest_path():return state_dir()/'installation.json'


def _comment(line):
    quote=None;escape=False
    for index,char in enumerate(line):
        if escape:escape=False;continue
        if quote=='"' and char=='\\':escape=True;continue
        if char in {'"',"'"}:
            if quote==char:quote=None
            elif quote is None:quote=char
        if char=='#' and quote is None and (index==0 or line[index-1].isspace()):return line[:index]
    return line


def scalar(value):
    if value in {'true','false'}:return value=='true'
    if value in {'null','~'}:return None
    if value=='{}':return {}
    if value.startswith('"'):
        try:result=json.loads(value)
        except ValueError as error:raise ProfileError('Invalid quoted value') from error
        if not isinstance(result,str):raise ProfileError('Expected a string')
        return result
    if value.startswith("'"):
        if not value.endswith("'") or len(value)<2:raise ProfileError('Invalid single-quoted value')
        inside=value[1:-1];remainder=inside.replace("''",'')
        if "'" in remainder:raise ProfileError('Escape single quotes by doubling them')
        return inside.replace("''","'")
    if re.fullmatch(r'-?[0-9]+',value):return int(value)
    if value[:1] in {'!','&','*','[','{','|','>','-','?','%','@','`'} or ': ' in value:raise ProfileError('Unsupported YAML construct; use nested mappings and scalar values')
    return value


def parse(text):
    if len(text.encode())>65536:raise ProfileError('Profile exceeds 64 KiB')
    text=text.lstrip('\ufeff')
    result={};stack=[(-2,result)]
    for number,original in enumerate(text.splitlines(),1):
        if '\t' in original:raise ProfileError(f'Line {number}: use spaces, not tabs')
        line=_comment(original).rstrip()
        if not line.strip():continue
        indent=len(line)-len(line.lstrip(' '))
        if indent%2 or indent>12:raise ProfileError(f'Line {number}: use two-space indentation')
        content=line.strip()
        if ':' not in content:raise ProfileError(f'Line {number}: expected key: value')
        key,value=content.split(':',1);key=key.strip();value=value.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*',key):raise ProfileError(f'Line {number}: unsupported key')
        while stack and indent<=stack[-1][0]:stack.pop()
        if not stack or indent!=stack[-1][0]+2:raise ProfileError(f'Line {number}: unexpected indentation')
        parent=stack[-1][1]
        if key in parent:raise ProfileError(f'Line {number}: duplicate key {key}')
        if not value:
            parent[key]={};stack.append((indent,parent[key]))
        else:parent[key]=scalar(value)
    return result


def dump(data,indent=0):
    lines=[]
    for key,value in data.items():
        prefix=' '*indent+key+':'
        if isinstance(value,dict):
            if value:lines.extend([prefix,dump(value,indent+2).rstrip()])
            else:lines.append(prefix+' {}')
        else:lines.append(prefix+' '+json.dumps(value,ensure_ascii=False))
    return '\n'.join(lines)+'\n'


def merge(base,patch):
    result=copy.deepcopy(base)
    for key,value in patch.items():
        if isinstance(value,dict) and isinstance(result.get(key),dict):result[key]=merge(result[key],value)
        else:result[key]=copy.deepcopy(value)
    return result


def read(path):
    try:return parse(path.read_text(encoding='utf-8'))
    except OSError as error:raise ProfileError('Cannot read profile: '+str(path)) from error


def all_apps(root):return [line.split('|') for line in (root/'data/apps.tsv').read_text().splitlines() if line and not line.startswith('#')]


def validate(profile,root=None):
    if not isinstance(profile,dict):raise ProfileError('Profile must be a mapping')
    unknown=set(profile)-set(DEFAULT)
    if unknown:raise ProfileError('Unknown profile keys: '+', '.join(sorted(unknown)))
    if type(profile.get('schema_version')) is not int or profile['schema_version']!=1:raise ProfileError('Unsupported schema_version; expected 1')
    if profile.get('language') not in {'en','pt-BR'}:raise ProfileError('Supported languages: en, pt-BR')
    for key in ['features','applications','environment','system','storage','vm']:
        if not isinstance(profile.get(key),dict):raise ProfileError(key+' must be a mapping')
    if set(profile['features'])!=set(FEATURES):raise ProfileError('Unknown or missing feature key')
    if any(type(value) is not bool for value in profile['features'].values()):raise ProfileError('Features must be true or false')
    if profile['features']['ai']:raise ProfileError('The local AI helper is not implemented; keep ai: false')
    for key,allowed in [('system',{'username','home'}),('storage',{'mount_points'}),('vm',{'username','autologin'})]:
        if set(profile[key])!=allowed:raise ProfileError('Unknown or missing '+key+' key')
    for section in ['system','vm']:
        user=profile[section]['username']
        if user is not None and (not isinstance(user,str) or not re.fullmatch(r'[a-z_][a-z0-9_-]{0,31}',user)):raise ProfileError('Invalid '+section+'.username')
    if profile['vm']['username'] in {None,'root'} or type(profile['vm']['autologin']) is not bool:raise ProfileError('VM requires username and boolean autologin')
    home=profile['system']['home']
    if home is not None and (not isinstance(home,str) or not Path(home).is_absolute()):raise ProfileError('system.home must be an absolute path or null')
    mounts=profile['storage']['mount_points']
    if not isinstance(mounts,dict) or any(not isinstance(k,str) or not isinstance(v,str) or not Path(v).is_absolute() for k,v in mounts.items()):raise ProfileError('storage.mount_points maps names to required existing absolute mount paths')
    known={row[0] for row in all_apps(root)} if root else None
    for app,value in profile['applications'].items():
        if type(value) is not bool or known is not None and app not in known:raise ProfileError('Unknown app or non-boolean application selection: '+app)
        if app in CORE and not value:raise ProfileError('The core browser and file manager must remain enabled')
        group=GROUPS.get(app) or ('games' if app in GAME_IDS else None)
        if group in GROUPS.values() and not value and profile['features'][group]:raise ProfileError('Disable features.'+group+' instead of its required app')
        if group and value and not profile['features'][group]:raise ProfileError('Enable features.'+group+' before enabling '+app)
    for key,value in profile['environment'].items():
        forbidden=key in {'HOME','PATH','USER','LOGNAME','SHELL','LANG','LANGUAGE','BASH_ENV','ENV','IFS','CDPATH','GCONV_PATH','GI_TYPELIB_PATH','QT_PLUGIN_PATH','SHELLOPTS','BASHOPTS','PS0','PS1','PS2','PS4','PROMPT_COMMAND','ZDOTDIR'} or key.startswith(('LD_','DYLD_','PYTHON','SUDO_','XDG_','DBUS_','GRANDMA_','LC_')) or any(word in key for word in ['TOKEN','PASSWORD','SECRET','API_KEY','PRIVATE_KEY'])
        if forbidden or not re.fullmatch(r'[A-Z_][A-Z0-9_]*',key) or not isinstance(value,str) or any(c in value for c in '\n\r\0'):
            raise ProfileError('Unsupported environment key/value: '+key)
    return profile


def check_patch(patch):
    for key in ['features','applications','environment','system','storage','vm']:
        if key in patch and not isinstance(patch[key],dict):raise ProfileError(key+' must be a mapping')
    return patch


def load(root,path=None):
    base=copy.deepcopy(DEFAULT)
    if os.environ.get('LANG','').startswith('pt_BR'):base['language']='pt-BR'
    saved=profile_path()
    prior=previous()
    if prior:base=merge(base,prior)
    if saved.is_file():
        raw=check_patch(read(saved))
        known=(prior or raw).get('features',{})
        if prior or set(raw)==set(DEFAULT):
            for key in FEATURES:
                if key not in known:base['features'][key]=False
        base=merge(base,raw)
        for key in ['environment','applications']:
            if key in raw:base[key]=copy.deepcopy(raw[key])
        if 'mount_points' in raw.get('storage',{}):base['storage']['mount_points']=copy.deepcopy(raw['storage']['mount_points'])
    if path is not None and Path(path).resolve()!=saved.resolve():
        patch=check_patch(read(Path(path)));base=merge(base,patch)
        for key in ['environment','applications']:
            if patch.get(key)=={}:base[key]={}
        if patch.get('storage',{}).get('mount_points')=={}:base['storage']['mount_points']={}
    if isinstance(base.get('environment'),dict):base['environment']={key:value for key,value in base['environment'].items() if value is not None}
    return validate(base,root)


def active():
    explicit=os.environ.get('GRANDMA_PROFILE_JSON')
    if explicit:return json.loads(explicit)
    applied=previous()
    if applied:return merge(DEFAULT,applied)
    if profile_path().is_file():return merge(DEFAULT,read(profile_path()))
    return copy.deepcopy(DEFAULT)


def feature(name):return active()['features'][name]
def selected(root,profile):
    return [row for row in all_apps(root) if profile['applications'].get(row[0],True) and profile['features'].get(GROUPS.get(row[0],'games' if row[0] in GAME_IDS else ''),True)]


def previous():
    try:return json.loads(manifest_path().read_text()).get('profile')
    except (FileNotFoundError,ValueError):return None


def diff(old,new,prefix=''):
    result=[]
    for key in sorted(set(old or {})|set(new)):
        name=prefix+key;a=(old or {}).get(key);b=new.get(key)
        if isinstance(a,dict) and isinstance(b,dict):result+=diff(a,b,name+'.')
        elif a!=b:result.append(dict(key=name,before=a,after=b))
    return result


def plan(root,profile):
    rows=selected(root,profile)
    return dict(schema_version=1,backend='fedora-kinoite',profile=profile,applications=[row[0] for row in rows],changes=diff(previous(),profile),removals=[],data_policy='retain existing applications and personal data')


def check_identity(profile):
    wanted=profile['system'];actual=pwd.getpwuid(os.getuid()).pw_name
    if wanted['username'] is not None and wanted['username']!=actual:raise ProfileError('Run as the existing target desktop user: '+wanted['username'])
    if wanted['home'] is not None and Path(wanted['home']).resolve()!=Path.home().resolve():raise ProfileError('Home differs. Prepare the account/home during OS installation; no files were moved.')
    for name,path in profile['storage']['mount_points'].items():
        if not Path(path).is_mount():raise ProfileError('Required mount is not mounted: '+path+'. Prepare it during OS installation.')


def private_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);temporary=path.with_suffix('.partial')
    temporary.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n');temporary.chmod(0o600);temporary.replace(path)


def save(profile):
    path=profile_path();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    temporary=path.with_suffix('.partial');temporary.write_text('# Grandma Linux preferences — schema 1\n'+dump(profile));temporary.chmod(0o600);temporary.replace(path)


def observe(root,profile):
    apps={}
    for row in all_apps(root):
        available=row[1]!='-' and shutil.which(row[1]) is not None
        for scope in ['--user','--system']:
            if available:break
            try:available=subprocess.run(['flatpak','info',scope,row[0]],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10).returncode==0
            except (OSError,subprocess.TimeoutExpired):available=False
        apps[row[0]]=bool(available)
    mounts=[]
    try:mounts=json.loads(subprocess.check_output(['findmnt','--json','--target',str(Path.home()),'--output','TARGET,SOURCE,FSTYPE'],text=True,timeout=10)).get('filesystems',[])
    except (OSError,ValueError,subprocess.SubprocessError):pass
    return dict(username=pwd.getpwuid(os.getuid()).pw_name,home=str(Path.home()),home_mount=mounts,applications=apps)


def begin(root,profile,mode):
    snapshot=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    path=state_dir()/'profile-snapshots'/f'{snapshot}.json'
    private_json(path,dict(id=snapshot,status='started',mode=mode,desired=profile,previous=previous(),saved_preferences_text=profile_path().read_text() if profile_path().is_file() else None,version=(root/'VERSION').read_text().strip()))
    save(profile);return path


def finish(path,status,root,profile,code):
    record=json.loads(path.read_text());record.update(status=status,exit_code=code,finished_at=datetime.now(timezone.utc).isoformat())
    if status=='complete':
        observed=observe(root,profile);record['observed']=observed
        manifest=json.loads(manifest_path().read_text());manifest.update(profile=profile,profile_snapshot=record['id'],observed=observed,profile_changes=diff(record.get('previous'),profile))
        private_json(manifest_path(),manifest)
    private_json(path,record)


def environment(profile):
    locale='pt_BR.UTF-8' if profile['language']=='pt-BR' else 'en_US.UTF-8'
    return dict(profile['environment'],LANG=locale,LANGUAGE='pt_BR:pt' if profile['language']=='pt-BR' else 'en_US:en')


def install_environment(profile):
    path=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))/'environment.d/90-grandma-linux.conf'
    if path.exists() and '# Grandma Linux managed' not in path.read_text():raise ProfileError('Refusing to replace personal environment file: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    lines=['# Grandma Linux managed — applied to new user sessions']
    for key,value in environment(profile).items():lines.append(key+'='+json.dumps(value.replace('$','$$'),ensure_ascii=False))
    temporary=path.with_suffix('.partial');temporary.write_text('\n'.join(lines)+'\n');temporary.chmod(0o600);temporary.replace(path)
    locale=environment(profile)['LANG']
    subprocess.run(['kwriteconfig6','--file','plasma-localerc','--group','Formats','--key','LANG',locale],check=True)
    subprocess.run(['kwriteconfig6','--file','plasma-localerc','--group','Translations','--key','LANGUAGE','pt_BR' if profile['language']=='pt-BR' else 'en_US'],check=True)
