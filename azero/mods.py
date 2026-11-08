"""Gestor de mods: archivos .jar en la carpeta mods/ de Minecraft.

El launcher instala los jars; los mods que requieren un mod loader
(Forge/Fabric/NeoForge) necesitan ademas ese loader instalado — la
mayoria de mods de Minecraft 1.12.1 son mods de Forge. Los loaders se
instalan desde los botones de la tarjeta Mods de Ajustes; sus perfiles
aparecen en Versiones y soportan herencia igual que OptiFine.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import paths


@dataclass
class ModInfo:
    name: str
    path: Path
    size: int
    title: str = ""
    version: str = ""
    forge: bool = False
    loader: str = ""


def mods_dir() -> Path:
    target = paths.MC_DIR / "mods"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _read_mod_metadata(names: set[str], jar: zipfile.ZipFile,
                       fallback: str) -> tuple[str, str]:
    """Extrae nombre/version del mod sin ejecutar nada (solo lectura del zip)."""
    try:
        for candidate in ("mcmod.info", "fabric.mod.json"):
            if candidate not in names:
                continue
            data = json.loads(jar.read(candidate).decode("utf-8", "replace"))
            if candidate == "mcmod.info":
                # Formato Forge 1.12.x: lista de mods o dict unico.
                entries = data if isinstance(data, list) else [data]
                first = entries[0] if entries else {}
                return (str(first.get("name") or fallback),
                        str(first.get("version") or ""))
            return (str(data.get("name") or fallback),
                    str(data.get("version") or ""))
        manifest = jar.read("META-INF/MANIFEST.MF").decode("utf-8", "replace")
        fields = {}
        for line in manifest.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip()] = value.strip()
        return (fields.get("Implementation-Title") or fallback,
                fields.get("Implementation-Version") or "")
    except Exception:  # noqa: BLE001 - metadatos opcionales
        return fallback, ""


def _names_look_forge(names: list[str]) -> bool:
    """Heuristica Forge/FML sobre la lista de entradas de un zip."""
    if "mcmod.info" in names:
        return True
    for name in names:
        lowered = name.lower()
        if "minecraftforge" in lowered or "/fml/" in lowered \
                or lowered.endswith("fml.class"):
            return True
    return False


def _loader_of(names: list[str]) -> str:
    """Loader del mod segun los metadatos dentro del jar.

    Orden importante: fabric.mod.json es exclusivo de Fabric;
    neoforge.mods.toml distingue NeoForge de Forge (que usa
    META-INF/mods.toml o mcmod.info); los jars Forge 1.13+ tambien
    llevan mods.toml, asi que NeoForge se comprueba antes.
    """
    name_set = set(names)
    lowered = {name.lower() for name in names}
    if "fabric.mod.json" in name_set:
        return "fabric"
    if "meta-inf/neoforge.mods.toml" in lowered:
        return "neoforge"
    if "mcmod.info" in name_set or "meta-inf/mods.toml" in lowered \
            or _names_look_forge(names):
        return "forge"
    return ""


def is_forge_mod(path: Path) -> bool:
    """Heuristica: el jar parece un mod de Forge/FML (mcmod.info o clases
    de MinecraftForge/FML en el interior). Solo lectura del zip."""
    try:
        with zipfile.ZipFile(path) as jar:
            return _names_look_forge(jar.namelist())
    except Exception:  # noqa: BLE001
        return False


def detect_loader(path: Path) -> str:
    """Tipo de loader que necesita el mod: fabric/neoforge/forge/""."""
    try:
        with zipfile.ZipFile(path) as jar:
            return _loader_of(jar.namelist())
    except Exception:  # noqa: BLE001
        return ""


def describe_mod(path: Path) -> tuple[str, str]:
    """Devuelve (titulo, version) de un jar; nunca lanza excepciones."""
    try:
        with zipfile.ZipFile(path) as jar:
            return _read_mod_metadata(set(jar.namelist()), jar, path.stem)
    except Exception:  # noqa: BLE001
        return path.stem, ""


def list_mods() -> list[ModInfo]:
    """Lista los .jar instalados en mods/, ordenados por nombre."""
    folder = mods_dir()
    mods = []
    for item in folder.iterdir():
        if not (item.is_file() and item.suffix.lower() == ".jar"):
            continue
        try:
            # Una sola apertura del zip: metadatos + deteccion de loader.
            with zipfile.ZipFile(item) as jar:
                names = jar.namelist()
                title, version = _read_mod_metadata(set(names), jar,
                                                    item.stem)
                loader = _loader_of(names)
                forge = loader in ("forge", "neoforge")
        except Exception:  # noqa: BLE001 - jar ilegible: datos minimos
            title, version, forge, loader = item.stem, "", False, ""
        mods.append(ModInfo(name=item.name, path=item,
                            size=item.stat().st_size,
                            title=title, version=version, forge=forge,
                            loader=loader))
    mods.sort(key=lambda mod: mod.name.lower())
    return mods


def _validate_jar(path: Path) -> None:
    if path.suffix.lower() != ".jar":
        raise ValueError("El archivo debe ser un .jar")
    if not zipfile.is_zipfile(path):
        raise ValueError("El archivo no es un jar valido (zip corrupto)")


def install_mod(source: Path) -> ModInfo:
    """Copia un .jar a mods/. Reemplaza si ya existe uno con el mismo nombre."""
    source = Path(source)
    _validate_jar(source)
    folder = mods_dir()
    target = folder / source.name
    shutil.copy2(source, target)
    title, version = describe_mod(target)
    loader = detect_loader(target)
    return ModInfo(name=target.name, path=target,
                   size=target.stat().st_size, title=title, version=version,
                   forge=loader in ("forge", "neoforge"), loader=loader)


def remove_mod(name: str) -> None:
    """Elimina un mod por nombre de archivo (solo dentro de mods/)."""
    folder = mods_dir()
    target = (folder / Path(name).name).resolve()
    # Blindaje: el nombre nunca debe escapar de mods/.
    if folder.resolve() not in target.parents or target == folder.resolve():
        raise ValueError("Nombre de mod invalido")
    if not target.is_file():
        raise FileNotFoundError(f"Mod no encontrado: {name}")
    target.unlink()
