#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the installed upstream GUI adapter without injecting desktop input."""
import os
os.environ.update(QT_QPA_PLATFORM='offscreen',LANG='pt_BR.UTF-8',LANGUAGE='pt_BR')
import importlib.util
import json
from pathlib import Path
import resource
import sys
import time
base=Path.home()/'.local/share/grandma-linux/translator'
sys.path.insert(0,str(base))
spec=importlib.util.spec_from_file_location('translator_ui',base/'translator-ui.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
app=module.QApplication([]);window=module.Window()
window.left_textEdit.setPlainText('Bom dia. Onde fica a estação de trem?')
assert not window.right_textEdit.toPlainText(), 'Typing should not start translation'
window.request_translation()
start=time.monotonic()
while window.worker_thread is not None and time.monotonic()-start<90:
 app.processEvents();time.sleep(.02)
app.processEvents()
output=window.right_textEdit.toPlainText()
assert output and output!='Bom dia. Onde fica a estação de trem?',output
assert window.windowTitle().startswith('Tradutor')
assert window.right_textEdit.isReadOnly()
assert window.left_language_combo.currentText()=='Português'
window.close();app.processEvents()
print(json.dumps(dict(passed=True,output=output,seconds=round(time.monotonic()-start,3),peak_rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,1)),ensure_ascii=False))
