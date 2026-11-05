"""Punto de entrada de la aplicacion (GUI y frozen)."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from . import APP_NAME, APP_VERSION
from .paths import ensure_dirs
from .settings import Settings
from .ui import theme
from .ui.main_window import MainWindow


def main() -> int:
    ensure_dirs()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} Launcher")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_NAME)

    theme.apply_theme(app)
    settings = Settings.load()
    window = MainWindow(settings)
    window.show()
    return app.exec()
