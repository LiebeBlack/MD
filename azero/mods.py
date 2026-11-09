"""Gestor de mods: archivos .jar en la carpeta mods/ de Minecraft.

El launcher instala los jars; los mods que requieren un mod loader
(Forge/Fabric/NeoForge) necesitan ademas ese loader instalado — la
mayoria de mods de Minecraft 1.12.1 son mods de Forge. Los loaders se
instalan desde los botones de la tarjeta Mods de Ajustes; sus perfiles
aparecen en Versiones y soportan herencia igual que OptiFine.
"""

from __future__ import annotations

import json
import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

try:  # Python 3.11+; en versiones anteriores los .toml se ignoran.
    import tomllib
except ImportError:  # pragma: no cover
    tomllib = None

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
    depends: dict = field(default_factory=dict)


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


# ---------------------------------------------------- dependencias del mod
def _read_depends(names: set[str], jar: zipfile.ZipFile) -> dict:
    """Dependencias declaradas por el mod (minecraft/java/loader).

    fabric.mod.json usa ``depends``; Forge/NeoForge usan
    META-INF/mods.toml o META-INF/neoforge.mods.toml con
    ``[[dependencies]]`` y ``modId``/``versionRange``.
    """
    depends: dict[str, str] = {}
    try:
        if "fabric.mod.json" in names:
            data = json.loads(
                jar.read("fabric.mod.json").decode("utf-8", "replace"))
            for key, value in (data.get("depends") or {}).items():
                depends[str(key)] = str(value)
            return depends
        lowered = {n.lower() for n in names}
        toml_name = ("meta-inf/neoforge.mods.toml"
                     if "meta-inf/neoforge.mods.toml" in lowered
                     else "meta-inf/mods.toml")
        actual = next((n for n in names if n.lower() == toml_name), None)
        if actual is None:
            return depends
        if tomllib is None:
            return depends
        data = tomllib.loads(jar.read(actual).decode("utf-8", "replace"))
        for dep in data.get("dependencies") or []:
            mod_id = str(dep.get("modId") or "").lower()
            version_range = str(dep.get("versionRange") or "").strip()
            if not version_range:
                continue
            if mod_id == "minecraft":
                depends["minecraft"] = version_range
            elif mod_id == "java":
                depends["java"] = version_range
            elif mod_id in ("fabricloader", "forge", "neoforge"):
                depends.setdefault("loader", version_range)
    except Exception:  # noqa: BLE001 - metadatos opcionales
        return {}
    return depends


_PREDICATE = re.compile(
    r"^\s*(~|>=|<=|>|<|=)?\s*v?(\d+(?:\.\d+){0,3})"
    r"(?:-[0-9A-Za-z.-]+)?\s*$")


def _version_tuple(text: str) -> tuple[int, ...]:
    # Solo el prefijo numerado: "1.21.1-pre4" -> (1,21,1,0), no (1,21,1,4).
    head = re.match(r"^v?(\d+(?:\.\d+)*)", text.strip())
    parts = [int(p) for p in head.group(1).split(".")] if head else []
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def _predicate_ok(operator: str, dep: tuple[int, ...],
                  target: tuple[int, ...]) -> bool:
    if operator == "~":
        # ~1.21.1 -> >=1.21.1 <1.22 ; ~26.3 -> >=26.3 <26.4
        upper = [dep[0], dep[1] + 1, 0, 0]
        return dep <= target < tuple(upper)
    if operator in (">=", ""):
        return target >= dep
    if operator == "<=":
        return target <= dep
    if operator == ">":
        return target > dep
    if operator == "<":
        return target < dep
    return target == dep  # "=" y sin operador: version exacta


def _compare(target: tuple[int, ...], op: str,
             bound: tuple[int, ...]) -> bool:
    if op in (">=", ""):
        return target >= bound
    if op == "<=":
        return target <= bound
    if op == ">":
        return target > bound
    if op == "<":
        return target < bound
    return target == bound


def _bound_check(raw: str, target: tuple[int, ...],
                 default_op: str) -> bool | None:
    """Un extremo del rango: '[', ']' dan inclusividad por defecto."""
    match = re.match(r"^(>=|>|<=|<|=)?\s*(.+)$", raw.strip())
    if not match:
        return None
    bound = _version_tuple(match.group(2))
    if bound == (0, 0, 0, 0):
        return None
    op = match.group(1) or default_op
    return _compare(target, op, bound)


def _range_matches(dep: str, target: tuple[int, ...]) -> bool | None:
    """Rango estilo Maven: ``[1.21,1.22)``, ``(1.21,]``, ``[,1.22)``."""
    dep = dep.strip()
    lower_inc = dep.startswith("[")
    upper_inc = dep.endswith("]")
    inner = dep[1:-1] if len(dep) > 1 and dep[-1] in ")]" else dep[1:]
    bounds = [b.strip() for b in inner.split(",")]
    lower_raw = bounds[0] if bounds else ""
    upper_raw = bounds[1] if len(bounds) > 1 else ""
    if lower_raw:
        ok = _bound_check(lower_raw, target,
                          ">=" if lower_inc else ">")
        if ok is not True:
            return ok
    if upper_raw:
        ok = _bound_check(upper_raw, target,
                          "<=" if upper_inc else "<")
        if ok is not True:
            return ok
    return True


def dep_matches(depends_value: str, version: str) -> bool | None:
    """True/False si la dependencia cubre ``version``; None si no se
    puede interpretar (versiones raras tipo 1.7.10-pre4)."""
    dep = (depends_value or "").strip()
    if not dep or dep in ("*", "any"):
        return True
    target = _version_tuple(version)
    if target == (0, 0, 0, 0):
        return None
    if dep.startswith(("[", "(")):
        return _range_matches(dep, target)
    verdict = True
    for token in re.split(r"[\s,]+", dep):
        token = token.strip().rstrip("-")
        if not token:
            continue
        # Wildcard "26.3.x" / "1.21.x": >=26.3.0 <26.4.0
        wild = re.match(r"^v?(\d+(?:\.\d+)*)\.?x$", token)
        if wild:
            numbers = [int(p) for p in wild.group(1).split(".")]
            lower = tuple(numbers + [0] * (4 - len(numbers)))[:4]
            if len(numbers) >= 2:
                upper = (numbers[0], numbers[1] + 1, 0, 0)
            else:
                upper = (numbers[0] + 1, 0, 0, 0)
            if not (lower <= target < upper):
                return False
            continue
        match = _PREDICATE.match(token)
        if not match:
            return None
        operator, raw = match.group(1) or "", match.group(2)
        dep_version = _version_tuple(raw)
        if dep_version == (0, 0, 0, 0):
            return None
        if not _predicate_ok(operator, dep_version, target):
            return False
    return verdict


def incompatible_mods(mods_list: list[ModInfo], mc_version: str
                      ) -> list[tuple[ModInfo, str]]:
    """Mods cuyo ``depends.minecraft`` excluye ``mc_version``."""
    bad = []
    for mod in mods_list:
        dep = (mod.depends or {}).get("minecraft")
        if not dep:
            continue
        if dep_matches(dep, mc_version) is False:
            bad.append((mod, dep))
    return bad


# NeoForge es compatible con mods Forge (lee mods.toml igual que Forge).
_ALLOWED_MOD_LOADERS = {
    "neoforge": {"forge", "neoforge"},
    "forge": {"forge"},
    "fabric": {"fabric"},
}


def incompatible_loader_mods(mods_list: list[ModInfo],
                             loader_kind: str) -> list[ModInfo]:
    """Mods cuyo loader no coincide con el del perfil elegido.

    Solo aplica cuando el perfil tiene loader: en vanilla/OptiFine el
    juego ignora mods/ y no hay crash que evitar. Los jars sin loader
    detectado (sin metadatos de mod) los ignoran ambos loaders."""
    if not loader_kind:
        return []
    allowed = _ALLOWED_MOD_LOADERS.get(loader_kind, {loader_kind})
    return [mod for mod in mods_list
            if mod.loader and mod.loader not in allowed]


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
            # Una sola apertura del zip: metadatos + loader + depends.
            with zipfile.ZipFile(item) as jar:
                names = jar.namelist()
                title, version = _read_mod_metadata(set(names), jar,
                                                    item.stem)
                loader = _loader_of(names)
                forge = loader in ("forge", "neoforge")
                depends = _read_depends(set(names), jar)
        except Exception:  # noqa: BLE001 - jar ilegible: datos minimos
            title, version, forge, loader = item.stem, "", False, ""
            depends = {}
        mods.append(ModInfo(name=item.name, path=item,
                            size=item.stat().st_size,
                            title=title, version=version, forge=forge,
                            loader=loader, depends=depends))
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
