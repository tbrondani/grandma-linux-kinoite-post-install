#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Single entry point for default installation, profiles and reconfiguration."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import profiles

ROOT=Path(__file__).resolve().parents[1]


def text(en,pt,language):return pt if language=='pt-BR' else en


def template(destination,dry_run=False):
    if dry_run:
        print((ROOT/'data/profile.example.yaml').read_text());return
    if destination.exists():raise profiles.ProfileError('Refusing to replace an existing file: '+str(destination))
    destination.write_text((ROOT/'data/profile.example.yaml').read_text());destination.chmod(0o600)
    print('Profile template: '+str(destination.resolve()))


def wizard(args):
    language=args.lang or (profiles.previous() or {}).get('language','en')
    say=lambda en,pt:print(text(en,pt,language))
    say('\nGrandma Linux · Installer','\nGrandma Linux · Instalador')
    print('─' * 44)
    if args.mode is None:
        say('  1  Install / repair\n  2  Reconfigure\n  3  Update Grandma Linux',
            '  1  Instalar / reparar\n  2  Reconfigurar\n  3  Atualizar Grandma Linux')
        print()
        choice=input(text('Choose an option','Escolha uma opção',language)+(' [2]: ' if profiles.manifest_path().exists() else ' [1]: ')).strip()
        if not choice:choice='2' if profiles.manifest_path().exists() else '1'
        if choice not in {'1','2','3'}:raise profiles.ProfileError('Choose 1, 2 or 3')
        args.mode={'1':'install','2':'reconfigure','3':'update'}[choice]
    else:choice={'install':'1','reconfigure':'2','update':'3'}[args.mode]
    if choice=='3':return True
    if args.config or args.from_snapshot:return True
    if profiles.profile_path().is_file():
        say('\nSaved profile:','\nPerfil salvo:')
        print('  '+str(profiles.profile_path()))
        print()
    answer=input(text('Use another custom profile? [y/N] ','Usar outro perfil personalizado? [s/N] ',language)).strip().lower()
    if answer in {'y','yes','s','sim'}:
        path=input(text('Existing YAML path (Enter to create a template): ','Caminho do YAML existente (Enter para criar um modelo): ',language)).strip()
        if path:args.config=Path(path).expanduser()
        else:
            destination=Path.cwd()/'grandma-profile.yaml';template(destination,args.dry_run)
            say('Edit the file, then run:','Edite o arquivo e execute:')
            if (Path.home()/'.local/bin/grandma-install').is_file():print(shlex.quote(str(Path.home()/'.local/bin/grandma-install'))+' --config '+shlex.quote(str(destination)))
            elif os.environ.get('GRANDMA_BOOTSTRAP_REF'):
                ref=os.environ['GRANDMA_BOOTSTRAP_REF']
                url='https://raw.githubusercontent.com/tbrondani/grandma-linux-kinoite-post-install/'+ref+'/install.sh'
                print('curl -fsSL '+shlex.quote(url)+' | GRANDMA_REF='+shlex.quote(ref)+' bash -s -- --config '+shlex.quote(str(destination)))
            else:print('bash '+shlex.quote(str(ROOT/'setup.sh'))+' --config '+shlex.quote(str(destination)))
            return False
    return True


def check_platform():
    if os.geteuid()==0:raise profiles.ProfileError('Run as the desktop user, without sudo')
    import platform
    release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
    if release.get('ID','').strip('\"')!='fedora' or release.get('VARIANT_ID','').strip('\"')!='kinoite' or platform.machine()!='x86_64':raise profiles.ProfileError('The supported backend is Fedora Kinoite x86_64')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,help='Use a custom YAML profile; unspecified values keep saved/default preferences.')
    parser.add_argument('--mode',choices=['install','reconfigure','update'])
    parser.add_argument('--update',action='store_true',help='Apply an already downloaded project update; reuse the saved profile.')
    parser.add_argument('--lang',choices=['en','en-US','pt-BR'])
    parser.add_argument('--dry-run',action='store_true');parser.add_argument('--yes',action='store_true')
    parser.add_argument('--interactive',action='store_true');parser.add_argument('--no-interactive',action='store_true')
    parser.add_argument('--template',type=Path,help='Create a commented YAML template and exit.')
    parser.add_argument('--from-snapshot',help='Reuse desired settings from a saved profile snapshot ID.')
    parser.add_argument('--list-snapshots',action='store_true')
    parser.add_argument('--list-apps',action='store_true',help='List the selectable application IDs.')
    args=parser.parse_args()
    snapshot=None;profile=None
    try:
        if args.update and args.mode is not None:raise profiles.ProfileError('Choose --update or --mode, not both')
        if args.config and args.from_snapshot:raise profiles.ProfileError('Choose --config or --from-snapshot, not both')
        if args.template:template(args.template,args.dry_run);return 0
        if args.list_apps:
            for row in profiles.all_apps(ROOT):print(row[0]+' — '+row[2]+' / '+row[3])
            return 0
        if args.list_snapshots:
            for path in sorted((profiles.state_dir()/'profile-snapshots').glob('*.json')):
                record=json.loads(path.read_text());print(record['id'],record['status'],record.get('version',''))
            return 0
        interactive=args.interactive or (sys.stdin.isatty() and not args.no_interactive and not args.yes and not args.update and not args.dry_run)
        if interactive and not wizard(args):return 0
        if args.mode=='update' and not args.update and not args.dry_run:
            command=[sys.executable,str(ROOT/'scripts/project_update.py'),'--apply']
            if args.lang:command.append('--lang='+('en' if args.lang=='en-US' else args.lang))
            if args.yes:command.append('--yes')
            if args.config:command+=['--config',str(args.config.resolve())]
            return subprocess.run(command).returncode
        if args.from_snapshot:
            import re
            if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}',args.from_snapshot):raise profiles.ProfileError('Invalid snapshot ID')
            path=profiles.state_dir()/'profile-snapshots'/f'{args.from_snapshot}.json'
            profile=profiles.validate(json.loads(path.read_text())['desired'],ROOT)
        else:profile=profiles.load(ROOT,args.config)
        if args.lang:profile['language']='en' if args.lang=='en-US' else args.lang
        if not args.update and not args.dry_run:
            current=(profiles.previous() or {}).get('language')
            profile['language']=profiles.confirm_language(profile['language'],current,
                (args.interactive or sys.stdin.isatty()) and not args.no_interactive)
        mode=args.mode or ('update' if args.update else 'reconfigure' if profiles.manifest_path().exists() else 'install')
        plan=profiles.plan(ROOT,profile)
        print(('\n' if interactive else '')+text('Installation plan','Plano de instalação',profile['language']),flush=True)
        if interactive and not args.dry_run:print('─' * 44)
        if args.dry_run or not interactive:print(json.dumps(dict(mode=mode,**plan),indent=2,ensure_ascii=False),flush=True)
        else:
            names={'accessibility':('Reading comfort','Conforto de leitura'),'theme':('Familiar appearance','Aparência familiar'),'offline_maps':('Offline maps','Mapas offline'),'dictionaries':('Dictionaries','Dicionários'),'translator':('Offline translator','Tradutor offline'),'games':('Games','Jogos'),'remote_support':('Remote support','Suporte remoto'),'backup':('Backup','Backup'),'ai':('AI','IA')}
            enabled=[text(*names[key],profile['language']) for key,value in profile['features'].items() if value]
            print(text('Enabled features:','Recursos ativados:',profile['language']))
            for name in enabled:print('  • '+name)
            print()
            print(text('Selected applications: ','Aplicativos selecionados: ',profile['language'])+str(len(plan['applications'])))
            print(text('Existing applications and personal files will be kept.','Os programas existentes e os arquivos pessoais serão mantidos.',profile['language']))
            print()
        if args.dry_run:return 0
        profiles.check_identity(profile)
        check_platform()
        if interactive and not args.yes:
            answer=input(text('Apply this plan? [y/N] ','Aplicar este plano? [s/N] ',profile['language'])).lower().strip()
            if answer not in {'y','yes','s','sim'}:return 0
        profiles.state_dir().mkdir(parents=True,exist_ok=True,mode=0o700)
        with (profiles.state_dir()/'installer.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise profiles.ProfileError('Another installation is running')
            snapshot=profiles.begin(ROOT,profile,mode)
            env=dict(os.environ,**profiles.environment(profile))
            env['GRANDMA_PROFILE_JSON']=json.dumps(profile);env['GRANDMA_PROFILE_RUN']='1'
            for key,value in profile['features'].items():env['GRANDMA_'+key.upper()]='1' if value else '0'
            with tempfile.TemporaryDirectory(prefix='grandma-selection-') as folder:
                manifest=Path(folder)/'apps.tsv';manifest.write_text(''.join('|'.join(row)+'\n' for row in profiles.selected(ROOT,profile)))
                env['GRANDMA_APPS_MANIFEST']=str(manifest)
                command=['bash',str(ROOT/'scripts/apply-profile.sh'),'--lang='+profile['language']]
                if mode!='install':command.append('--update')
                code=subprocess.run(command,env=env).returncode
            if code==0:
                profiles.install_environment(profile)
                from project_update import record_install
                record_install(ROOT)
            profiles.finish(snapshot,'complete' if code==0 else 'reboot-required' if code==75 else 'failed',ROOT,profile,code)
            if code==0:
                print(text('Profile applied. Personal data and disabled components were retained.','Perfil aplicado. Dados pessoais e componentes desabilitados foram preservados.',profile['language']))
                print(text('Language and environment changes apply to new login sessions.','Mudanças de idioma e ambiente valem para as próximas sessões de login.',profile['language']))
            if code==75:print(text('Restart and run the same installer command again. Your profile is saved.','Reinicie e execute o mesmo comando. Seu perfil está salvo.',profile['language']))
            return code
    except (profiles.ProfileError,OSError,ValueError,KeyError,TypeError) as error:
        if snapshot is not None:
            try:profiles.finish(snapshot,'failed',ROOT,profile,2)
            except OSError:pass
        print('Configuration: '+str(error),file=sys.stderr);return 2
    except (KeyboardInterrupt,EOFError):
        if snapshot is not None:
            try:profiles.finish(snapshot,'cancelled',ROOT,profile,130)
            except OSError:pass
        return 130

if __name__=='__main__':raise SystemExit(main())
