#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""User-level desktop defaults. Never replace Plasma libraries or personal files."""
import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
from desktop import entries, launcher_names
from theme import install as install_theme, adjust_menu_opacity


def write_ini(path, updates):
    cfg = configparser.ConfigParser(interpolation=None, strict=False)
    cfg.optionxform = str
    if path.exists():
        cfg.read(path)
    for section, values in updates.items():
        if section not in cfg:
            cfg[section] = {}
        cfg[section].update(values)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and '# Grandma Linux managed' not in path.read_text() and not path.with_suffix(path.suffix + '.before-grandma').exists():
        shutil.copy2(path, path.with_suffix(path.suffix + '.before-grandma'))
    with path.open('w') as stream:
        stream.write('# Grandma Linux managed\n')
        cfg.write(stream, space_around_delimiters=False)


def configure(root, dry_run=False):
    if dry_run:
        print('Configure task menu, file associations, double-click, Flameshot, and Se7en Aero.')
        return
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    data = Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    apps = data / 'applications'
    installed = {}
    for app_id, native, en, pt in entries(root):
        installed[app_id] = next(name for name in launcher_names(app_id, native) if (apps / name).is_file())
    for key, value in [('SingleClick', 'false'), ('MiddleClickPaste', 'false')]:
        subprocess.run(['kwriteconfig6', '--file', 'kdeglobals', '--group', 'KDE', '--key', key, value], check=True)
    # MIME associations use the actual overridden upstream desktop filenames.
    mapping = {}
    for types, app_id in [
        (['text/html','x-scheme-handler/http','x-scheme-handler/https'], 'com.brave.Browser'),
        (['application/pdf'], 'org.kde.okular'),
        (['image/jpeg','image/png','image/webp','image/gif'], 'org.kde.gwenview'),
        (['video/mp4','video/x-matroska','video/x-msvideo','video/webm','video/quicktime','audio/mpeg','audio/flac','audio/ogg','audio/mp4','audio/x-wav'], 'org.videolan.VLC'),
        (['application/vnd.openxmlformats-officedocument.wordprocessingml.document','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','application/vnd.openxmlformats-officedocument.presentationml.presentation'], 'org.onlyoffice.desktopeditors')]:
        mapping.update({mime: installed[app_id] for mime in types})
    write_ini(config / 'mimeapps.list', {'Default Applications': mapping})
    # Task folders use explicit desktop IDs to avoid listing an app twice.
    groups = [
        ('Internet', 'Internet', ['com.brave.Browser','org.mozilla.firefox']),
        ('Files', 'Arquivos e documentos', ['org.kde.dolphin','org.onlyoffice.desktopeditors','org.kde.okular','org.kde.kwrite','org.kde.ark']),
        ('Media', 'Fotos e mídia', ['org.kde.gwenview','org.videolan.VLC','org.kde.kamoso']),
        ('Sharing', 'Celular e compartilhamento', ['org.localsend.localsend_app','org.kde.kdeconnect']),
        ('Reading', 'Leitura e escrita', ['com.ktechpit.omnidict']),
        ('Utilities', 'Utilitários', ['org.kde.kcalc','org.flameshot.Flameshot','org.kde.kolourpaint','org.kde.filelight','io.missioncenter.MissionCenter','app.organicmaps.desktop']),
        ('Games', 'Jogos', [app_id for app_id in installed if app_id in {'org.kde.kpat','org.kde.kmines','org.kde.ksudoku','org.kde.kmahjongg','org.kde.palapeli','org.kde.kblocks','org.kde.kapman'}]),
    ]
    menu = ET.Element('Menu')
    ET.SubElement(menu,'Name').text = 'Applications'
    ET.SubElement(menu,'DefaultAppDirs')
    ET.SubElement(menu,'DefaultDirectoryDirs')
    for name, pt, ids in groups:
        filename = f'grandma-{name}.directory'
        write_ini(data / 'desktop-directories' / filename, {'Desktop Entry': {'Type':'Directory','Name':name,'Name[pt_BR]':pt,'Icon': 'applications-games' if name == 'Games' else 'folder'}})
        section = ET.SubElement(menu,'Menu')
        ET.SubElement(section,'Name').text = name
        ET.SubElement(section,'Directory').text = filename
        include = ET.SubElement(section,'Include')
        for app_id in ids:
            ET.SubElement(include,'Filename').text = installed[app_id]
        if name == 'Internet':
            ET.SubElement(include,'Filename').text = 'grandma-whatsapp.desktop'
    tools = ET.SubElement(menu,'Menu')
    ET.SubElement(tools,'Name').text='System'
    write_ini(data / 'desktop-directories/grandma-System.directory', {'Desktop Entry': {'Type':'Directory','Name':'System','Name[pt_BR]':'Sistema','Icon':'preferences-system'}})
    ET.SubElement(tools,'Directory').text='grandma-System.directory'
    include=ET.SubElement(tools,'Include')
    for filename in ('systemsettings.desktop','org.kde.discover.desktop','org.kde.konsole.desktop'):
        ET.SubElement(include,'Filename').text=filename
    menu_path=config / 'menus/plasma-applications.menu'
    menu_path.parent.mkdir(parents=True, exist_ok=True)
    if menu_path.exists() and '<!-- Grandma Linux managed -->' not in menu_path.read_text() and not menu_path.with_suffix('.menu.before-grandma').exists():
        shutil.copy2(menu_path, menu_path.with_suffix('.menu.before-grandma'))
    ET.indent(menu)
    menu_path.write_text('<?xml version="1.0"?>\n<!-- Grandma Linux managed -->\n<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN" "http://www.freedesktop.org/standards/menu-spec/1.0/menu.dtd">\n'+ET.tostring(menu, encoding='unicode'))
    # Save screenshots to the user's localized Pictures folder, including Flatpak config.
    pictures=Path(subprocess.run(['xdg-user-dir','PICTURES'], capture_output=True, text=True, check=True).stdout.strip())
    if not pictures.is_absolute() or pictures == Path.home():
        raise RuntimeError('Configure a Pictures folder before setting screenshot storage.')
    captures=pictures / 'Screenshots'
    captures.mkdir(parents=True, exist_ok=True)
    for path in (config / 'flameshot/flameshot.ini', Path.home() / '.var/app/org.flameshot.Flameshot/config/flameshot/flameshot.ini'):
        write_ini(path, {'General': {'savePath':str(captures),'savePathFixed':'true','saveAfterCopy':'true','copyOnDoubleClick':'true','filenamePattern':'%Y-%m-%d_%H-%M-%S','saveAsFileExtension':'png'}})
    install_theme(root,data)
    adjust_menu_opacity(data)
    subprocess.run(['plasma-apply-colorscheme','Win7OS'],check=True)
    subprocess.run(['plasma-apply-desktoptheme','Se7enAeroStyle'],check=True)
    for file,group,key,value in [
        ('kdeglobals','KDE','LookAndFeelPackage','Se7enAero'),
        ('kdeglobals','KDE','widgetStyle','fusion'),
        ('kdeglobals','Icons','Theme','Win11'),
        ('kwinrc','org.kde.kdecoration2','library','org.kde.kwin.aurorae'),
        ('kwinrc','org.kde.kdecoration2','theme','__aurorae__svg__Se7enAero'),
        ('kwinrc','org.kde.kdecoration2','ButtonsOnLeft','M'),
        ('kwinrc','org.kde.kdecoration2','ButtonsOnRight','IAX')]:
        subprocess.run(['kwriteconfig6','--file',file,'--group',group,'--key',key,value],check=True)
    subprocess.run(['gdbus','call','--session','--dest','org.kde.KWin','--object-path','/KWin','--method','org.kde.KWin.reconfigure'],check=True)
    start_icon=data / 'icons/hicolor/scalable/apps/grandma-start.svg'
    start_icon.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(root / 'assets/start.svg',start_icon)
    script = '''
var ds = desktops();
for (var i=0; i<ds.length; i++) {
 ds[i].currentConfigGroup=["General"];
 ds[i].writeConfig("arrangement", 1);
 ds[i].writeConfig("alignment", 0);

}
var ps=panels();
if (ps.length===0) ps=[new Panel];
ps[0].location="bottom";
ps[0].height=46;
ps[0].floating=false;
for (var p=0; p<ps.length; p++) {
 var widgets=ps[p].widgets();
 for (var w=0; w<widgets.length; w++) {
  if (widgets[w].type==="org.kde.plasma.kickoff" || widgets[w].type==="org.kde.plasma.kicker") {
   widgets[w].currentConfigGroup=["General"];
   widgets[w].writeConfig("icon", START_ICON);
  }
 }
}
'''.replace('START_ICON',json.dumps(str(start_icon)))
    subprocess.run(['gdbus','call','--session','--dest','org.kde.plasmashell','--object-path','/PlasmaShell','--method','org.kde.PlasmaShell.evaluateScript',script], check=True)
    subprocess.run(['kbuildsycoca6','--noincremental'], check=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true')
    configure(Path(__file__).resolve().parent.parent,parser.parse_args().dry_run)
