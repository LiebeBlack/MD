"""Rutas de datos del launcher (modo portable por defecto)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .constants import APP_NAME

APP_ROOT = Path(__file__).resolve().parent.parent


def _default_data_dir() -> Path:
    """Directorio de datos por defecto.

    En desarrollo o en un ejecutable portable los datos viven junto al
    codigo. En una instalacion congelada (PyInstaller) dentro de Program
    Files no hay permisos de escritura, asi que se usa %APPDATA%.
    """
    override = os.environ.get("AZEROCRAFT_DATA")
    if override:
        return Path(override).expanduser()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        probe = exe_dir / ".azero_write_test"
        try:
            probe.touch()
            probe.unlink()
            return exe_dir / "data"
        except OSError:
            roaming = Path(os.environ.get("APPDATA") or Path.home())
            return roaming / APP_NAME / "data"
    return APP_ROOT / "data"


DATA_DIR = _default_data_dir().expanduser()

SETTINGS_FILE = DATA_DIR / "settings.json"
CACHE_DIR = DATA_DIR / "cache"
JAVA_DIR = DATA_DIR / "java"
LOGS_DIR = DATA_DIR / "logs"

MC_DIR = DATA_DIR / "minecraft"
VERSIONS_DIR = MC_DIR / "versions"
LIBRARIES_DIR = MC_DIR / "libraries"
ASSETS_DIR = MC_DIR / "assets"
NATIVES_DIR = MC_DIR / "natives"


def ensure_dirs() -> None:
    for path in (DATA_DIR, CACHE_DIR, JAVA_DIR, LOGS_DIR, MC_DIR,
                 VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR):
        path.mkdir(parents=True, exist_ok=True)


def version_dir(version_id: str) -> Path:
    return VERSIONS_DIR / version_id


def version_json_path(version_id: str) -> Path:
    return version_dir(version_id) / f"{version_id}.json"


def version_jar_path(version_id: str) -> Path:
    return version_dir(version_id) / f"{version_id}.jar"


def natives_dir(version_id: str) -> Path:
    return NATIVES_DIR / version_id
