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

def guide():
    desktop=Path(subprocess.check_output(['xdg-user-dir','DESKTOP'],text=True).strip())
    if not desktop.is_absolute() or desktop==Path.home():
        raise RuntimeError(text('Configure the desktop folder first.','Configure a pasta da área de trabalho primeiro.'))
    manual=desktop/'.grandma-linux-manual.html'
    if not manual.is_file():
        raise RuntimeError(text('The manual is missing. Run Grandma Linux setup again.','O manual não foi encontrado. Execute a configuração Grandma Linux novamente.'))
    # The existing Brave Flatpak can read xdg-desktop. No new filesystem
    # permission, server or additional application is needed for this file.
    native=shutil.which('brave-browser')
    if native:
        subprocess.Popen([native,'--app='+manual.as_uri(),'--window-size=1200,820'],start_new_session=True)
    elif shutil.which('flatpak') and subprocess.run(['flatpak','info','com.brave.Browser'],capture_output=True).returncode==0:
        subprocess.Popen(['flatpak','run','com.brave.Browser','--app='+manual.as_uri(),'--window-size=1200,820'],start_new_session=True)
    else:
        subprocess.run(['xdg-open',manual.as_uri()],check=True)


def reading():
    from reading import apply
    choice=dialog('--menu',text('Choose the text size you find easiest to read.','Escolha o tamanho de texto mais confortável para você.'),
        'standard',text('Atkinson — 12 pt','Atkinson — 12 pt'),
        'large',text('Atkinson — 14 pt','Atkinson — 14 pt'),
        'restore',text('Restore previous font and pointer size','Restaurar fonte e tamanho do ponteiro anteriores'),
        'settings',text('More font settings','Mais opções de fonte'))
    if choice=='settings':
        subprocess.Popen(['systemsettings','kcm_fonts']);return
    apply(choice)
    message('Reading settings saved. Reopen applications to see the changes. You can restore the previous settings here.',
            'Configurações de leitura salvas. Reabra os aplicativos para ver as mudanças. Você pode restaurar as configurações anteriores aqui.')


class UpdateProgress:
    """Native busy dialog that stays open for the complete project update."""
    def __enter__(self):
        import dbus
        reference=dialog('--progressbar',text('Preparing the update…','Preparando a atualização…'),'0',title=text('Grandma Linux update','Atualização Grandma Linux')).split()
        if len(reference)!=2:raise RuntimeError('Cannot open update progress dialog.')
        self.interface=dbus.Interface(dbus.SessionBus().get_object(*reference),'org.kde.kdialog.ProgressDialog')
        return self
    def __call__(self,stage,value=None):
        labels={
            'download':text('Downloading update','Baixando atualização')+(' — '+str(value)+'%' if value is not None else ''),
            'verify':text('Verifying the update package…','Verificando o pacote da atualização…'),
            'install':text('Installing the update. Keep the computer on.','Instalando a atualização. Mantenha o computador ligado.'),
            'complete':text('Update complete.','Atualização concluída.'),
        }
        try:self.interface.setLabelText(labels.get(stage,stage))
        except Exception:pass  # Closing the window must not interrupt a package operation.
    def __exit__(self,*args):
        try:self.interface.close()
        except Exception:pass


def updates():
    from project_update import apply, UpdateError, available_update, installed_version, state_dir, discard_pending
    version=installed_version()
    choice=dialog('--menu',text('Installed Grandma Linux: ','Grandma Linux instalado: ')+version,
                  'system',text('System and applications','Sistema e aplicativos'),
                  'project',text('Grandma Linux setup and manual','Configuração e manual Grandma Linux'),
                  'log',text('View the last project update log','Ver o registro da última atualização do projeto'),
                  'restart',text('Start the project update again','Recomeçar a atualização do projeto'))
    if choice=='system':
        subprocess.Popen(['plasma-discover','--mode','update']);return
    if choice=='log':
        path=state_dir()/'project-update.log'
        if path.is_file():view(path,text('Update log','Registro da atualização'))
        else:message('No project update has run yet.','Nenhuma atualização do projeto foi executada ainda.')
        return
    try:
        if choice=='restart':
            dialog('--yesno',text('Discard the saved update package? The next check will look for the latest release.',
                                  'Descartar o pacote de atualização salvo? A próxima busca procurará a versão mais recente.'))
            discard_pending()
            message('Saved update cleared. Select the project update to check again.','Pacote salvo removido. Selecione a atualização do projeto para buscar novamente.')
            return
        with UpdateProgress() as progress:
            release,pending=available_update()
        if release is None:
            message('No stable Grandma Linux release is available yet.','Ainda não há uma versão estável do Grandma Linux disponível.');return
        if not release['available']:
            message('Grandma Linux is up to date.','O Grandma Linux está atualizado.');return
        action=text('Resume Grandma Linux ','Retomar Grandma Linux ') if pending else text('Install Grandma Linux ','Instalar Grandma Linux ')
        dialog('--yesno',action+release['tag']+'?\n'+text(
            'Your wallpaper, reading preferences and backup settings are preserved.',
            'Seu papel de parede, preferências de leitura e configurações de backup serão preservados.'))
        with UpdateProgress() as progress:code=apply(release,'pt-BR' if PT else 'en',progress)
        if code==75:
            message('Restart the computer, then open Updates → Grandma Linux to finish. The verified package is saved.',
                    'Reinicie o computador. Depois abra Atualizações → Grandma Linux para concluir. O pacote verificado está salvo.')
        else:message('Grandma Linux update complete.','Atualização do Grandma Linux concluída.')
    except UpdateError as error:
        messages={
            'network':('Cannot connect to GitHub. Check your internet connection.','Não foi possível acessar o GitHub. Verifique a conexão com a internet.'),
            'busy':('An update is already running.','Uma atualização já está em andamento.'),
        }
        en,pt=messages.get(str(error),('The update could not be completed. Open Updates → View the last project update log. You can retry the update.',
            'Não foi possível concluir a atualização. Abra Atualizações → Ver o registro da última atualização do projeto. Você pode tentar novamente.'))
        dialog('--error',text(en,pt))


def help_menu(backup):
    choice=dialog('--menu',text('How can we help?','Como podemos ajudar?'),
        'guide',text('How to use','Como usar'),'remote',text('Remote support','Suporte remoto'),
        'info',text('Support information','Informações para suporte'))
    if choice=='guide':guide()
    elif choice=='info':support_information(backup)
    elif choice=='remote':subprocess.Popen([sys.executable,str(BASE/'remote-support-session.py')])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['backup','recover','guide','help','info','scheduled-backup','updates','reading']);args=parser.parse_args()
    backup=Backup()
    try:
        if args.action=='scheduled-backup':backup.run()
        else:{'backup':backup_menu,'recover':recover,'guide':lambda b:guide(),'help':help_menu,'info':support_information,'updates':lambda b:updates(),'reading':lambda b:reading()}[args.action](backup)
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
