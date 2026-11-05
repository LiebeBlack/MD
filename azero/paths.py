"""Rutas de datos del launcher y del juego.

El juego (versiones, libraries, assets, mods) vive siempre en la carpeta
.minecraft oficial de Mojang, mas las carpetas .minecraft adicionales que
el usuario registre con el escaner de Versiones.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .constants import APP_NAME

APP_ROOT = Path(__file__).resolve().parent.parent


def _data_root() -> Path:
    """Raiz estable donde vive la configuracion del launcher.

    - Desarrollo: la carpeta del proyecto.
    - Ejecutable en carpeta escribible: junto al .exe.
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


def _official_mc_dir() -> Path:
    """Carpeta .minecraft oficial de Mojang.

    Se usa siempre para que versiones, mundos, resourcepacks, shaderpacks
    y mods sean compatibles con el launcher oficial y otros launchers.
    Los datos internos del launcher (ajustes, cache, Java, logs) siguen
    viviendo en DATA_DIR.
    """
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / ".minecraft"
    return Path.home() / ".minecraft"


def _derive() -> None:
    """Recalcula todas las rutas derivadas de DATA_DIR."""
    global DATA_DIR, SETTINGS_FILE, CACHE_DIR, JAVA_DIR, LOGS_DIR
    global MC_DIR, VERSIONS_DIR, LIBRARIES_DIR, ASSETS_DIR, NATIVES_DIR

    DATA_DIR = _default_data_dir().expanduser()
    SETTINGS_FILE = DATA_DIR / "settings.json"
    CACHE_DIR = DATA_DIR / "cache"
    JAVA_DIR = DATA_DIR / "java"
    LOGS_DIR = DATA_DIR / "logs"

    MC_DIR = _official_mc_dir()
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


# ------------------------------------------------- carpetas .minecraft extra
# Raices .minecraft adicionales registradas por el usuario (escaner de la
# pestana Versiones). Sus perfiles de version se reconocen igual que los
# oficiales; las descargas nuevas siempre van a la raiz oficial.
EXTRA_MC_DIRS: list[Path] = []


def set_extra_mc_dirs(dirs) -> None:
    """Fija las raices .minecraft adicionales (rutas absolutas)."""
    global EXTRA_MC_DIRS
    seen: list[Path] = []
    for item in dirs:
        try:
            candidate = Path(item).expanduser().resolve()
        except (OSError, ValueError):
            continue
        if candidate == MC_DIR or candidate in seen:
            continue
        seen.append(candidate)
    EXTRA_MC_DIRS = seen


def mc_roots() -> list[Path]:
    """Todas las raices .minecraft conocidas (oficial primero)."""
    return [MC_DIR, *EXTRA_MC_DIRS]


def versions_dirs() -> list[Path]:
    """Carpetas versions/ de todas las raices conocidas.

    Usa el global VERSIONS_DIR (puede estar redirigido) como primera
    entrada; las raices extra siempre derivan de su raiz .minecraft.
    """
    return [VERSIONS_DIR,
            *(root / "versions" for root in EXTRA_MC_DIRS)]


def find_version_json(version_id: str) -> Path | None:
    """Primer <version>.json encontrado en cualquier raiz conocida."""
    for versions_dir in versions_dirs():
        candidate = versions_dir / version_id / f"{version_id}.json"
        if candidate.is_file():
            return candidate
    return None


def find_version_dir(version_id: str) -> Path | None:
    """Carpeta de la version donde exista su perfil o su jar."""
    for versions_dir in versions_dirs():
        candidate = versions_dir / version_id
        if candidate.is_dir() and (
                (candidate / f"{version_id}.json").is_file()
                or (candidate / f"{version_id}.jar").is_file()):
            return candidate
    return None


def find_version_jar(version_id: str) -> Path | None:
    """Primer <version>.jar existente en cualquier raiz conocida."""
    for versions_dir in versions_dirs():
        candidate = versions_dir / version_id / f"{version_id}.jar"
        if candidate.is_file():
            return candidate
    return None
