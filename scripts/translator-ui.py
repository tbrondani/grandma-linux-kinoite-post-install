#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Small localized adapter for the upstream Argos Translate GUI."""
import os
os.environ.update(ARGOS_CHUNK_TYPE='MINISBD', ARGOS_DEVICE_TYPE='cpu', ARGOS_INTRA_THREADS='2',
                  ARGOS_INTER_THREADS='1', ARGOS_COMPUTE_TYPE='int8', OMP_NUM_THREADS='2')
from argostranslategui import gui
from argostranslategui.gui import GUIWindow
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QPushButton

PT = os.environ.get('LANG', '').startswith('pt_BR') or os.environ.get('LANGUAGE', '').startswith('pt_BR')
NAMES = {'pt':'Português','en':'Inglês','es':'Espanhol','fr':'Francês','de':'Alemão','it':'Italiano'}

class SafeTranslationThread(gui.TranslationThread):
    def run(self):
        try:
            super().run()
        except Exception:
            self.send_text_update.emit('Não foi possível traduzir esta frase.' if PT else 'Could not translate this sentence.')

gui.TranslationThread = SafeTranslationThread


class Window(GUIWindow):
    def translate(self):
        # Upstream calls this during construction and on every edit. Wait for
        # an explicit button press, so small edits do not queue CPU work.
        if getattr(self, '_translate_requested', False):
            self._translate_requested = False
            if self.left_textEdit.toPlainText().strip():
                super().translate()

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Tradutor — Argos Translate' if PT else 'Translator — Argos Translate')
        self.left_textEdit.clear(); self.right_textEdit.clear()
        self.right_textEdit.setReadOnly(True)
        self.left_textEdit.setAcceptRichText(False)
        self.left_textEdit.setPlaceholderText('Digite ou cole uma frase.' if PT else 'Type or paste a sentence.')
        self.right_textEdit.setPlaceholderText('A tradução aparece aqui.' if PT else 'The translation appears here.')
        for combo, default in [(self.left_language_combo,'pt'),(self.right_language_combo,'en')]:
            for i,language in enumerate(self.languages):
                if PT: combo.setItemText(i,NAMES.get(language.code,language.name))
                if language.code==default:combo.setCurrentIndex(i)
        # Models are managed by setup. Keep the everyday interface offline.
        self.manage_packages_action.setVisible(False)
        self.about_action.setText('Sobre' if PT else 'About')
        self.button=QPushButton('Traduzir' if PT else 'Translate')
        self.button.clicked.connect(self.request_translation)
        self.window_layout.addWidget(self.button)
        self.poll=QTimer(self);self.poll.timeout.connect(self.refresh);self.poll.start(100)
        self.resize(800,420)

    def request_translation(self):
        self._translate_requested=True
        self.button.setEnabled(False)
        self.translate()

    def refresh(self):
        self.button.setEnabled(self.worker_thread is None)

    def closeEvent(self,event):
        if self.worker_thread is not None:
            self.worker_thread.wait()
        super().closeEvent(event)

if __name__=='__main__':
    app=QApplication([]);window=Window();window.show();app.exec_()
