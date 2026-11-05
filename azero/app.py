"""Punto de entrada de la aplicacion (GUI y frozen)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import (QApplication, QDialog, QDialogButtonBox,
                             QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QWidget)

from . import APP_NAME, APP_VERSION, paths
from .settings import Settings
from .ui import theme
from .ui.main_window import MainWindow


def _browse(edit: QLineEdit, parent: QWidget) -> None:
    selected = QFileDialog.getExistingDirectory(
        parent, "Elegir carpeta de datos", edit.text() or str(Path.home())
    )
    if selected:
        edit.setText(selected)


def _ask_data_dir(parent: QWidget) -> Path | None:
    """Primer arranque: el usuario elige donde guardar los datos del juego."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Carpeta de datos")
    dialog.setModal(True)
    dialog.setMinimumWidth(560)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(22, 20, 22, 18)
    layout.setSpacing(12)

    title = QLabel("¿Dónde quieres guardar Minecraft y los datos del launcher?")
    title.setStyleSheet("font-size: 13pt; font-weight: 700;")
    layout.addWidget(title)
    layout.addWidget(QLabel(
        "Por defecto se usa una carpeta 'data' junto al programa "
        "(portable). Puedes elegir otra unidad o carpeta, por ejemplo "
        "D:\\Games\\AZeroCraft."
    ))

    default = paths.DATA_DIR
    row = QHBoxLayout()
    row.setSpacing(8)
    edit = QLineEdit(str(default))
    browse = QPushButton("Examinar…")
    browse.clicked.connect(lambda: _browse(edit, dialog))
    row.addWidget(edit, 1)
    row.addWidget(browse)
    layout.addLayout(row)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return Path(edit.text().strip() or str(default))


def main() -> int:
    first_run = not paths.SETTINGS_FILE.exists() \
        and "AZEROCRAFT_DATA" not in os.environ

    paths.ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} Launcher")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)

    theme.apply_theme(app)

    if first_run:
        helper = QWidget()
        helper.setWindowTitle(f"{APP_NAME} Launcher")
        helper.resize(1, 1)
        chosen = _ask_data_dir(helper)
        helper.deleteLater()
        if chosen is not None:
            paths.set_data_dir(chosen)

    settings = Settings.load()
    # Reaplica el tema con la preferencia guardada (el dialogo de primer
    # arranque ya mostro el tema claro por defecto).
    theme.apply_theme(app, settings.ui_theme)
    window = MainWindow(settings)
    window.show()
    return app.exec()
