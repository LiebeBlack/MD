"""Deteccion de carpetas .minecraft en ubicaciones arbitrarias.

El escaner de la pestana Versiones permite registrar raices .minecraft
que no estan en la ubicacion oficial (otra unidad, otra carpeta, otro
nombre). Solo se reconocen perfiles de version; las descargas nuevas
siguen yendo a la raiz oficial.
"""

from __future__ import annotations

from pathlib import Path


def _has_version_profiles(folder: Path) -> bool:
    """True si la carpeta contiene subcarpetas con un .json de version."""
    try:
        for child in folder.iterdir():
            if child.is_dir() and any(child.glob("*.json")):
                return True
    except OSError:
        return False
    return False


def detect_mc_root(start) -> Path | None:
    """Localiza la raiz .minecraft (carpeta que contiene versions/).

    Acepta rutas flexibles:
    - la propia raiz .minecraft (…/.minecraft con versions/ dentro);
    - la carpeta versions/ directamente;
    - una carpeta que CONTENGA una raiz .minecraft en un subdirectorio
      inmediato (p. ej. Roaming, otra unidad o carpeta de juegos);
    - una carpeta con perfiles de version sueltos (versions desplazada).
    Devuelve la raiz .minecraft o None si no se reconoce ninguna.
    """
    start = Path(start).expanduser()
    try:
        start = start.resolve()
    except OSError:
        return None
    if not start.is_dir():
        return None

    # 1) start es la raiz .minecraft: contiene versions/ con perfiles.
    versions = start / "versions"
    if versions.is_dir() and _has_version_profiles(versions):
        return start

    # 2) start ES la carpeta versions/ (o equivalente con otro nombre).
    if _has_version_profiles(start):
        return start.parent

    # 3) Busca una raiz .minecraft en los subdirectorios inmediatos.
    try:
        children = sorted(start.iterdir())
    except OSError:
        return None
    for child in children:
        if not child.is_dir():
            continue
        child_versions = child / "versions"
        if child_versions.is_dir() \
                and _has_version_profiles(child_versions):
            return child
    return None
