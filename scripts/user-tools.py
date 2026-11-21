#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small native KDE dialogs for backup, first steps and support."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from backup import Backup, private_json

PT=os.environ.get('LANG','').startswith('pt_BR') or os.environ.get('LANGUAGE','').startswith('pt_BR')
BASE=Path(__file__).resolve().parent

def text(en,pt):return pt if PT else en
class Cancelled(Exception):pass

def dialog(option,*args,title=None):
    result=subprocess.run(['kdialog','--title',title or text('Grandma Linux','Grandma Linux'),option,*map(str,args)],capture_output=True,text=True)
    if result.returncode:raise Cancelled()
    return result.stdout.strip()

def message(en,pt):dialog('--msgbox',text(en,pt))

def view(path,title):dialog('--textbox',path,'760','540',title=title)

def status(backup):
    if not backup.config_path.exists():return text('Backup is not configured.','O backup não está configurado.')
    state=json.loads(backup.status_path.read_text()) if backup.status_path.exists() else {}
    last=state.get('last_success')
    if last:
        last=datetime.fromisoformat(last).astimezone().strftime('%d/%m/%Y %H:%M')
    output=text('Last successful backup: ','Última cópia concluída: ')+(last or text('none yet','nenhuma ainda'))
    if state.get('error'):output+='\n'+text('The last attempt failed. Open Backup and try again.','A última tentativa falhou. Abra Backup e tente novamente.')
    return output

def require_backup(backup):
    if backup.config_path.exists():return
    folder=dialog('--getexistingdirectory',Path.home(),title=text('Select the saved Grandma Linux backup folder','Escolha a pasta do backup Grandma Linux'))
    backup.configure_local(folder)

def recover(backup, allow_existing=True):
    versions=sorted(backup.snapshots(),key=lambda s:s['time'],reverse=True) if backup.config_path.exists() else []
    if not versions and not allow_existing:
        message('There are no backup versions in this folder.','Não há versões de backup nesta pasta.');return
    choices=[]
    for item in versions:
        date=datetime.fromisoformat(item['time'].replace('Z','+00:00')).astimezone().strftime('%d/%m/%Y %H:%M')
        choices.extend([item['id'],date])
    if allow_existing:choices.extend(['existing',text('Open a saved backup folder','Abrir uma pasta de backup guardada')])
    selected=dialog('--menu',text('Choose a backup version.','Escolha uma versão do backup.'),*choices)
    if selected=='existing':
        folder=Path(dialog('--getexistingdirectory',Path.home(),title=text('Select the saved backup folder','Escolha a pasta do backup guardado'))).resolve()
        marker=json.loads((folder/'grandma-backup.json').read_text())
        # Read another bundle without changing the current automatic backup.
        with tempfile.TemporaryDirectory(prefix='grandma-recovery-') as temporary:
            reader=Backup(config_dir=Path(temporary),state_dir=backup.state_dir)
            private_json(reader.config_path,dict(root=str(folder),id=marker['id'],sources=[]))
            reader.validate(reader.config())
            recover(reader,allow_existing=False)
        return
    parent=dialog('--getexistingdirectory',Path.home(),title=text('Where should recovered files be saved?','Onde guardar os arquivos recuperados?'))
    dialog('--passivepopup',text('Recovering files. Please wait.','Recuperando arquivos. Aguarde.'),'5')
    destination=backup.restore(selected,parent)
    message('Recovery complete. A new folder will open.','Recuperação concluída. Uma pasta nova será aberta.')
    subprocess.Popen(['xdg-open',str(destination)])

def backup_menu(backup):
    choice=dialog('--menu',status(backup),'now',text('Back up now','Fazer cópia agora'),
                  'restore',text('Recover files','Recuperar arquivos'),'folder',text('Open backup folder','Abrir pasta do backup'))
    if choice=='restore':recover(backup)
    elif choice=='folder':
        require_backup(backup);subprocess.Popen(['xdg-open',backup.config()['root']])
    elif choice=='now':
        if not backup.config_path.exists():backup.configure_local()
        dialog('--passivepopup',text('Creating a backup. Please wait.','Criando uma cópia. Aguarde.'),'5')
        backup.run();message('Backup complete.','Cópia concluída.')

def support_information(backup):
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key,value=line.split('=',1);release[key]=value.strip('"')
    memory=dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines())
    cpu=next((line.split(':',1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name')),'unknown')
    lines=['Grandma Linux',release.get('PRETTY_NAME','Linux'),platform.release(),cpu,
           text('Memory: ','Memória: ')+str(round(int(memory['MemTotal'].split()[0])/1024/1024,1))+' GiB',
           text('Free disk space: ','Espaço livre: ')+str(round(shutil.disk_usage(Path.home()).free/1e9,1))+' GB',status(backup)]
    app_list=subprocess.run(['flatpak','list','--app','--columns=application,version'],capture_output=True,text=True)
    lines+=['',text('Applications','Aplicativos'),app_list.stdout.strip()]
    path=backup.state_dir/'support-information.txt';path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    path.write_text('\n'.join(lines)+'\n');path.chmod(0o600)
    view(path,text('Support information','Informações para suporte'))

def render_manual_topic(manual, topic):
    lines=[topic['title'], '']
    if topic.get('before'):lines.extend([topic['before'], ''])
    lines.extend(f"{number}. {step}" for number,step in enumerate(topic['steps'],1))
    lines.extend(['',topic['result']])
    if topic.get('tip'):lines.extend(['',topic['tip']])
    lines.extend(['',manual['back']])
    return '\n'.join(lines)+'\n'


def guide():
    language='pt-BR' if PT else 'en'
    while True:
        manual=json.loads((BASE/'guides'/f'manual.{language}.json').read_text())
        choices=['__language__','English' if language=='pt-BR' else 'Português (Brasil)']
        for topic in manual['topics']:choices.extend([topic['id'],topic['title']])
        try:
            selected=dialog('--menu',manual['prompt'],*choices,title=manual['title'])
        except Cancelled:
            return
        if selected=='__language__':
            language='en' if language=='pt-BR' else 'pt-BR'
            continue
        topic=next(topic for topic in manual['topics'] if topic['id']==selected)
        # kdialog reads a plain local file. No browser permissions, internet,
        # Python GUI environment or permanent temporary files are needed.
        with tempfile.TemporaryDirectory(prefix='grandma-manual-') as folder:
            page=Path(folder)/'page.txt'
            page.write_text(render_manual_topic(manual,topic),encoding='utf-8')
            try:view(page,manual['title']+' — '+topic['title'])
            except Cancelled:pass


def help_menu(backup):
    choice=dialog('--menu',text('How can we help?','Como podemos ajudar?'),
        'guide',text('How to use','Como usar'),'remote',text('Remote support','Suporte remoto'),
        'info',text('Support information','Informações para suporte'))
    if choice=='guide':guide()
    elif choice=='info':support_information(backup)
    elif choice=='remote':subprocess.Popen([sys.executable,str(BASE/'remote-support-session.py')])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['backup','recover','guide','help','info','scheduled-backup']);args=parser.parse_args()
    backup=Backup()
    try:
        if args.action=='scheduled-backup':backup.run()
        else:{'backup':backup_menu,'recover':recover,'guide':lambda b:guide(),'help':help_menu,'info':support_information}[args.action](backup)
    except Cancelled:pass
    except Exception as error:
        if args.action=='scheduled-backup':
            # Preserve last successful timestamp even if validation fails before restic starts.
            backup.record(error=str(error),last_attempt=datetime.now().astimezone().isoformat())
            if shutil.which('notify-send'):
                subprocess.run(['notify-send',text('Backup needs attention','O backup precisa de atenção'),text('Open Backup in Utilities.','Abra Backup em Utilitários.')],check=False)
            raise SystemExit(1)
        try:dialog('--error',text('Could not complete this action. Open Help → Support information.\n','Não foi possível concluir. Abra Ajuda → Informações para suporte.\n')+str(error))
        except Cancelled:pass
        raise SystemExit(1)
