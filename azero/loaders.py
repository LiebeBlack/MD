"""Loaders de mods: Fabric y NeoForge (Forge/OptiFine ya tienen modulo).

Fabric se instala con su instalador oficial en modo consola
(``client -dir ... -mcversion ... -loader ...``); NeoForge usa el mismo
instalador que Forge (``--installClient``), con su propio maven en
maven.neoforged.net. Ambos escriben un perfil <version>.json en
versions/ que el launcher reconoce igual que los de Forge/OptiFine.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

from . import paths
from .constants import USER_AGENT
from .forge import _download, _ensure_launcher_profiles
from .install import TaskContext, prepare
from .java import JavaRuntime, select_runtime
from .manifest import load_version_profile, required_java_major
from .util import read_json, write_json

# ------------------------------------------------------------------ fabric
_FABRIC_META = "https://meta.fabricmc.net/v2"
_FABRIC_MAVEN = "https://maven.fabricmc.net/net/fabricmc/fabric-installer"

# --------------------------------------------------------------- neoforge
_NEOFORGE_LEGACY_META = (
    "https://maven.neoforged.net/releases/net/neoforged/forge/"
    "maven-metadata.xml")
_NEOFORGE_NEW_META = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/"
    "maven-metadata.xml")
_NEOFORGE_LEGACY_MAVEN = (
    "https://maven.neoforged.net/releases/net/neoforged/forge")
_NEOFORGE_NEW_MAVEN = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge")

LOADER_KINDS = ("fabric", "neoforge", "forge", "optifine")


def loader_kind(version_id: str) -> str:
    """Tipo de perfil por su nombre. 'neoforge' antes que 'forge'
    porque un id neoforge tambien contiene la subcadena 'forge'."""
    lower = version_id.lower()
    for kind in ("optifine", "neoforge", "fabric", "forge"):
        if kind in lower:
            return kind
    return ""


def installed_loader_profiles() -> dict[str, list[str]]:
    """Perfiles de loaders instalados, agrupados por tipo."""
    grouped: dict[str, list[str]] = {kind: [] for kind in LOADER_KINDS}
    for profile_id in _all_local_profiles():
        kind = loader_kind(profile_id)
        if kind:
            grouped[kind].append(profile_id)
    return {kind: sorted(ids) for kind, ids in grouped.items() if ids}


def find_loader_profile(kind: str, mc_version: str) -> str | None:
    """Perfil instalado de un loader para una version de MC."""
    if kind == "neoforge":
        return _find_profile(mc_version, ("neoforge", "forge"),
                             check_json=_is_neoforged)
    if kind in ("fabric",):
        return _find_profile(mc_version, ("fabric-loader", "fabric"))
    return None


def has_loader_profile(kind: str) -> bool:
    return bool(installed_loader_profiles().get(kind))


def _all_local_profiles() -> list[str]:
    from .manifest import local_profiles
    return local_profiles()


# ------------------------------------------------------------- utilidades
def _fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _fetch_json(url: str) -> object:
    return json.loads(_fetch_text(url))


def _meta_cache(kind: str, mc_version: str) -> Path:
    return paths.CACHE_DIR / "loaders" / f"{kind}-{mc_version}.json"


def _read_meta_cache(kind: str, mc_version: str) -> dict | None:
    return read_json(_meta_cache(kind, mc_version))


def _write_meta_cache(kind: str, mc_version: str, payload: dict) -> None:
    try:
        _meta_cache(kind, mc_version).parent.mkdir(
            parents=True, exist_ok=True)
        write_json(_meta_cache(kind, mc_version), payload)
    except OSError:
        pass


def _parse_maven_versions(xml_text: str) -> list[str]:
    """Versiones de un maven-metadata.xml (orden del archivo)."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    versions = root.findall(".//{*}version")
    return [node.text.strip() for node in versions
            if node.text and node.text.strip()]


def _version_sort_key(version: str) -> list[int]:
    return [int(part) if part.isdigit() else 0
            for part in re.split(r"[.-]", version)]


def _choose_stable(versions: list[str]) -> str:
    """«latest» sin beta/alpha/rc; si no hay, la ultima disponible."""
    stable = [v for v in versions
              if not re.search(r"beta|alpha|rc|pre", v, re.IGNORECASE)]
    pool = stable or versions
    if not pool:
        raise RuntimeError("No hay builds publicados para esta version.")
    return max(pool, key=_version_sort_key)


def _find_profile(mc_version: str, needles: tuple[str, ...],
                  check_json=None) -> str | None:
    """Perfil local cuyo nombre contiene alguna aguja y hereda de MC.

    ``check_json(payload)`` exige un segundo criterio (p. ej. libraries
    net.neoforged) para perfiles legacy de NeoForge que se llaman forge-*:
    evita confundirlos con un Forge real de MinecraftForge.
    """
    for versions_dir in paths.versions_dirs():
        try:
            children = sorted(versions_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or not (child / f"{child.name}.json").exists():
                continue
            lower = child.name.lower()
            if not any(needle in lower for needle in needles):
                continue
            payload = load_version_profile(child.name)
            if payload is None:
                continue
            if payload.get("inheritsFrom") != mc_version \
                    and not child.name.startswith(mc_version):
                continue
            if check_json is None:
                return child.name
            if check_json(payload):
                return child.name
    return None


def _installer_java(mc_version: str, java_path: str,
                    log) -> JavaRuntime:
    """Runtime para el instalador: el declarado o el compatible mas cercano."""
    payload = load_version_profile(mc_version) or {}
    java_major = required_java_major(payload) if payload else 17
    # El instalador no es el juego: admite cualquier Java igual o mas
    # reciente que el declarado (max_major=99) y prefiere el major mas
    # cercano, p. ej. un instalador que pide 17 no salta a Java 25.
    runtime = (select_runtime(java_major, java_path, max_major=99,
                              prefer_newest=False)
               or select_runtime(17, java_path, max_major=99,
                                 prefer_newest=False)
               or select_runtime(8, java_path, max_major=99,
                                 prefer_newest=False))
    if runtime is None:
        raise RuntimeError(
            "No se encontro Java para ejecutar el instalador. Activa "
            "'descargar Java automaticamente' en Ajustes.")
    return runtime


# ------------------------------------------------------------------ FABRIC
def _fabric_meta(mc_version: str, offline: bool, log) -> dict:
    """Versiones del instalador y del loader para la version de MC."""
    cached = _read_meta_cache("fabric", mc_version)
    if offline:
        if cached:
            return cached
        raise RuntimeError(
            f"Sin conexion y sin datos de Fabric en cache para "
            f"Minecraft {mc_version}.")
    installer_list = _fetch_json(f"{_FABRIC_META}/versions/installer")
    installers = [item["version"] for item in installer_list
                  if isinstance(item, dict) and item.get("version")]
    if not installers:
        raise RuntimeError("Fabric no publico ningun instalador.")
    loader_list = _fetch_json(
        f"{_FABRIC_META}/versions/loader/{mc_version}")
    loaders = [item["loader"]["version"] for item in loader_list
               if isinstance(item, dict)
               and isinstance(item.get("loader"), dict)
               and item["loader"].get("version")]
    if not loaders:
        raise RuntimeError(
            f"Fabric no tiene loader para Minecraft {mc_version}.")
    payload = {
        "installer": _choose_stable(installers),
        "loader": loaders[0],  # la API ya viene ordenada de mas nueva
    }
    _write_meta_cache("fabric", mc_version, payload)
    log(f"Fabric: instalador {payload['installer']}, "
        f"loader {payload['loader']} para MC {mc_version}")
    return payload


def install_fabric(mc_version: str, java_path: str = "", log=print,
                   ctx: TaskContext | None = None,
                   offline: bool = False) -> str:
    """Instala Fabric para ``mc_version`` y devuelve el perfil creado."""
    meta = _fabric_meta(mc_version, offline, log)
    installer_version = meta["installer"]
    loader_version = meta["loader"]
    jar_name = f"fabric-installer-{installer_version}.jar"
    url = f"{_FABRIC_MAVEN}/{installer_version}/{jar_name}"
    installer = _download(url, paths.CACHE_DIR / "fabric" / jar_name, log)

    log(f"Instalando Fabric loader {loader_version} para "
        f"Minecraft {mc_version}…")
    # El cliente base debe existir: el instalador no usa
    # -downloadMinecraft para no duplicar descargas ni hashes.
    prepare(mc_version, ctx or TaskContext(log=log), with_assets=False,
            offline=offline)
    _ensure_launcher_profiles(mc_version)

    runtime = _installer_java(mc_version, java_path, log)
    command = [
        str(runtime.java), "-jar", str(installer),
        "client", "-dir", str(paths.MC_DIR),
        "-mcversion", mc_version,
        "-loader", loader_version,
    ]
    log("Ejecutando el instalador de Fabric…")
    result = subprocess.run(command, cwd=str(paths.MC_DIR),
                            capture_output=True, text=True,
                            timeout=600, check=False)
    if result.returncode != 0:
        tail = (result.stderr or result.stdout or "").strip()[-400:]
        raise RuntimeError(
            f"El instalador de Fabric fallo (codigo "
            f"{result.returncode}){': ' + tail if tail else '.'}")

    profile = _find_profile(mc_version, ("fabric-loader", "fabric"))
    if not profile:
        raise RuntimeError(
            "El instalador de Fabric termino pero no se encontro el "
            "perfil en versions/.")
    log(f"Fabric instalado: perfil '{profile}'.")
    return profile


# --------------------------------------------------------------- NEOFORGE
def _neoforge_short_prefix(mc_version: str) -> str:
    """Prefijo de version de NeoForge para el versionado de Minecraft.

    MC 1.21.1 -> "21.1.", MC 26.1.2 -> "26.1." (versionado calendario).
    """
    parts = mc_version.split(".")
    major = parts[0] if parts else "1"
    minor = parts[1] if len(parts) > 1 else "0"
    patch = parts[2] if len(parts) > 2 else "0"
    if major == "1":
        return f"{minor}.{patch}."
    return f"{major}.{minor}."


def _neoforge_meta(mc_version: str, offline: bool, log) -> dict:
    """Build de NeoForge para la version de MC (legacy o nueva API)."""
    cached = _read_meta_cache("neoforge", mc_version)
    if offline:
        if cached:
            return cached
        raise RuntimeError(
            f"Sin conexion y sin datos de NeoForge en cache para "
            f"Minecraft {mc_version}.")

    # API legacy (net.neoforged:forge): las versiones empiezan por la
    # version completa de MC, p. ej. "1.20.1-47.1.106".
    try:
        legacy_xml = _fetch_text(_NEOFORGE_LEGACY_META)
        legacy = [v for v in _parse_maven_versions(legacy_xml)
                  if v.startswith(f"{mc_version}-")]
    except Exception:  # noqa: BLE001 - se prueba la API nueva
        legacy = []
    if legacy:
        payload = {"version": _choose_stable(legacy), "api": "legacy"}
    else:
        # API nueva (net.neoforged:neoforge): prefijo corto.
        xml_text = _fetch_text(_NEOFORGE_NEW_META)
        prefix = _neoforge_short_prefix(mc_version)
        versions = [v for v in _parse_maven_versions(xml_text)
                    if v.startswith(prefix)]
        if not versions:
            raise RuntimeError(
                f"NeoForge no tiene builds para Minecraft {mc_version}.")
        payload = {"version": _choose_stable(versions), "api": "new"}

    _write_meta_cache("neoforge", mc_version, payload)
    log(f"NeoForge {payload['version']} ({payload['api']}) para "
        f"MC {mc_version}")
    return payload


def _is_neoforged(payload: dict) -> bool:
    for library in payload.get("libraries") or []:
        if str(library.get("name", "")).startswith("net.neoforged"):
            return True
    return False


def install_neoforge(mc_version: str, java_path: str = "", log=print,
                     ctx: TaskContext | None = None,
                     offline: bool = False) -> str:
    """Instala NeoForge para ``mc_version`` y devuelve el perfil creado."""
    meta = _neoforge_meta(mc_version, offline, log)
    version = meta["version"]
    if meta["api"] == "legacy":
        artifact, maven = "forge", _NEOFORGE_LEGACY_MAVEN
    else:
        artifact, maven = "neoforge", _NEOFORGE_NEW_MAVEN
    jar_name = f"{artifact}-{version}-installer.jar"
    url = f"{maven}/{version}/{jar_name}"
    installer = _download(url, paths.CACHE_DIR / "neoforge" / jar_name, log)

    log(f"Instalando NeoForge {version} para Minecraft {mc_version}…")
    prepare(mc_version, ctx or TaskContext(log=log), with_assets=False,
            offline=offline)
    _ensure_launcher_profiles(mc_version)

    runtime = _installer_java(mc_version, java_path, log)
    command = [str(runtime.java), "-jar", str(installer),
               "--installClient", str(paths.MC_DIR)]
    log("Ejecutando el instalador de NeoForge…")
    try:
        result = subprocess.run(command, cwd=str(paths.MC_DIR),
                                capture_output=True, text=True,
                                timeout=600, check=False)
    except subprocess.TimeoutExpired:
        result = None
    if result is None or result.returncode != 0:
        tail = ""
        if result is not None:
            tail = (result.stderr or result.stdout or "").strip()[-400:]
        # Respaldo: instalador grafico oficial.
        java = runtime.javaw if runtime.javaw.exists() else runtime.java
        log("La instalacion silenciosa no esta disponible; abriendo el "
            "instalador grafico de NeoForge…")
        subprocess.Popen([str(java), "-jar", str(installer)],
                         cwd=str(paths.MC_DIR))
        return version

    # "forge" en las agujas cubre los perfiles legacy de NeoForge, que se
    # llaman forge-*; check_json exige libraries net.neoforged para no
    # confundirlos con un Forge de MinecraftForge real.
    profile = _find_profile(mc_version, ("neoforge", "forge"),
                            check_json=_is_neoforged)
    if not profile:
        raise RuntimeError(
            "El instalador de NeoForge termino pero no se encontro el "
            "perfil en versions/.")
    log(f"NeoForge instalado: perfil '{profile}'.")
    return profile


INSTALLERS = {
    "fabric": install_fabric,
    "neoforge": install_neoforge,
}
