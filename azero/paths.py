"""Rutas de datos del launcher (modo portable por defecto)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .constants import APP_NAME

APP_ROOT = Path(__file__).resolve().parent.parent


def _data_root() -> Path:
    """Raiz estable donde vive la configuracion del launcher.

    - Desarrollo: la carpeta del proyecto (portable).
    - Ejecutable en carpeta escribible (portable): junto al .exe.
    - Instalado en Program Files: %APPDATA%\\AZeroCraft.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        probe = exe_dir / ".azero_write_test"
        try:
            probe.touch()
            probe.unlink()
            return exe_dir
        except OSError:
            roaming = Path(os.environ.get("APPDATA") or Path.home())
            return roaming / APP_NAME
    return APP_ROOT


DATA_ROOT = _data_root()
_MARKER_NAME = "data-dir.txt"


def _marker_path() -> Path:
    return DATA_ROOT / _MARKER_NAME


def _default_data_dir() -> Path:
    """Prioridad: AZEROCRAFT_DATA > eleccion del primer arranque > ./data."""
    override = os.environ.get("AZEROCRAFT_DATA")
    if override:
        return Path(override).expanduser()
    marker = _marker_path()
    try:
        if marker.exists():
            custom = marker.read_text(encoding="utf-8").strip()
            if custom:
                return Path(custom).expanduser()
    except OSError:
        pass
    return DATA_ROOT / "data"


def _derive() -> None:
    """Recalcula todas las rutas derivadas de DATA_DIR."""
    global DATA_DIR, SETTINGS_FILE, CACHE_DIR, JAVA_DIR, LOGS_DIR
    global MC_DIR, VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR, NATIVES_DIR

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


_derive()


def set_data_dir(path: Path | str) -> Path:
    """Fija una carpeta de datos personalizada y persiste la eleccion.

    La eleccion se guarda en DATA_ROOT/data-dir.txt para que sobreviva a
    reinicios y viaje con la instalacion portable.
    """
    target = Path(path).expanduser().resolve()
    try:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        _marker_path().write_text(str(target), encoding="utf-8")
    except OSError:
        pass
    _derive()
    ensure_dirs()
    return DATA_DIR


def clear_data_dir_override() -> None:
    """Vuelve al directorio de datos por defecto (borra la eleccion)."""
    try:
        _marker_path().unlink(missing_ok=True)
    except OSError:
        pass
    _derive()


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
