from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QPushButton, QVBoxLayout

from .translations import translate


class PreferencesDialog(QDialog):
    def __init__(self, language: str, parent=None) -> None:
        super().__init__(parent)
        self.language = language

        self.language_combo = QComboBox()
        self.language_combo.addItem("", "en")
        self.language_combo.addItem("", "es")
        self.language_combo.setCurrentIndex(self.language_combo.findData(language))

        self.language_label = QLabel()
        self.install_button = QPushButton()
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)

        self.form = QFormLayout()
        self.form.addRow(self.language_label, self.language_combo)

        layout = QVBoxLayout(self)
        layout.addLayout(self.form)
        layout.addWidget(self.install_button)
        layout.addWidget(self.button_box)

        self.retranslate(language)

    def retranslate(self, language: str) -> None:
        self.language = language
        self.setWindowTitle(translate(language, "dialog_preferences"))
        self.language_combo.setItemText(0, translate(language, "lang_english"))
        self.language_combo.setItemText(1, translate(language, "lang_spanish"))
        self.language_label.setText(translate(language, "prefs_language"))
        self.install_button.setText(translate(language, "prefs_install_launcher"))
        self.button_box.button(QDialogButtonBox.Ok).setText(translate(language, "prefs_close"))

    def selected_language(self) -> str:
        return str(self.language_combo.currentData())
