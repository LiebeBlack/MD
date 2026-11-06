"""Punto de entrada de la aplicacion (GUI y frozen)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog,
                             QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
                             QWidget)

from . import APP_NAME, APP_VERSION, paths
from .settings import Settings
from .ui import theme
from .ui.main_window import MainWindow
from .ui.widgets import Card, faint_label, make_button, muted_label


def _browse(edit: QLineEdit, parent: QWidget) -> None:
    selected = QFileDialog.getExistingDirectory(
        parent, "Elegir carpeta de datos", edit.text() or str(Path.home())
    )
    if selected:
        edit.setText(selected)


def _center_dialog(dialog: QDialog) -> None:
    screen = dialog.screen() or QApplication.primaryScreen()
    if screen is None:
        return
    dialog.adjustSize()
    geometry = dialog.frameGeometry()
    geometry.moveCenter(screen.availableGeometry().center())
    dialog.move(geometry.topLeft())


def _ask_data_dir(parent: QWidget) -> Path | None:
    """Primer arranque: el usuario elige donde guardar los datos del juego."""
    dialog = QDialog(parent)
    dialog.setWindowTitle("Carpeta de datos")
    dialog.setWindowIcon(theme.app_icon())
    dialog.setModal(True)
    dialog.setMinimumWidth(580)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(20, 18, 20, 16)
    layout.setSpacing(12)

    head = QHBoxLayout()
    head.setSpacing(12)
    icon = QLabel()
    icon.setPixmap(theme.app_icon().pixmap(44, 44))
    icon.setFixedSize(44, 44)
    head.addWidget(icon)
    titles = QVBoxLayout()
    titles.setContentsMargins(0, 0, 0, 0)
    titles.setSpacing(2)
    title = QLabel("¿Dónde quieres guardar los datos del launcher?")
    title.setObjectName("pageTitle")
    title.setWordWrap(True)
    subtitle = QLabel(
        "Elige una carpeta escribible; el juego sigue usando tu "
        ".minecraft oficial.")
    subtitle.setObjectName("pageSubtitle")
    subtitle.setWordWrap(True)
    titles.addWidget(title)
    titles.addWidget(subtitle)
    head.addLayout(titles, 1)
    layout.addLayout(head)

    card = Card(margins=16, spacing=10)
    card.body.addWidget(muted_label(
        "Por defecto se usa 'data' junto al launcher o tu perfil. "
        "Puedes elegir otra unidad, por ejemplo D:\\Games\\AZeroCraft."))
    default = paths.DATA_DIR
    row = QHBoxLayout()
    row.setSpacing(8)
    edit = QLineEdit(str(default))
    browse = make_button(
        "Examinar…", "ghost", "Elegir otra carpeta",
        lambda: _browse(edit, dialog))
    row.addWidget(edit, 1)
    row.addWidget(browse)
    card.body.addLayout(row)
    card.body.addWidget(faint_label(f"Carpeta sugerida: {default}"))
    layout.addWidget(card)

    note = faint_label(
        "Versiones, mundos, mods y resourcepacks siguen en tu "
        ".minecraft oficial.")
    note.setWordWrap(True)
    layout.addWidget(note)

    buttons = QHBoxLayout()
    buttons.setSpacing(8)
    buttons.addStretch(1)
    buttons.addWidget(make_button(
        "Cancelar", "ghost", "Volver a la carpeta por defecto",
        dialog.reject))
    continue_button = make_button(
        "Continuar", "primary", "Usar esta carpeta de datos",
        dialog.accept)
    continue_button.setDefault(True)
    continue_button.setAutoDefault(True)
    buttons.addWidget(continue_button)
    layout.addLayout(buttons)

    _center_dialog(dialog)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return Path(edit.text().strip() or str(default))


def main() -> int:
    first_run = not paths.SETTINGS_FILE.exists() \
        and "AZEROCRAFT_DATA" not in os.environ

    paths.ensure_dirs()
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
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
