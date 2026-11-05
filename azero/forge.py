"""Soporte Forge: descarga el instalador oficial y lo abre para el usuario.

Forge se instala con su propio instalador grafico (el launcher lo lanza
con la JVM adecuada); una vez instalado, Forge lee la carpeta mods/ y los
jars anadidos desde el launcher funcionan.
"""

from __future__ import annotations

import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from . import paths
from .constants import USER_AGENT
from .java import select_runtime
from .manifest import load_version_profile, write_version_profile
from .util import human_size

_FORGE_MAVEN = "https://files.minecraftforge.net/net/minecraftforge/forge"
_MAVEN_DL = "https://maven.minecraftforge.net/net/minecraftforge/forge"
_PROMOS_URL = f"{_FORGE_MAVEN}/promotions_slim.json"


def _fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def latest_forge_version(mc_version: str, log=print) -> str:
    """Version de Forge recomendada para la version de MC indicada."""
    try:
        promos = _fetch_json(_PROMOS_URL)
        promo = promos.get("promos", promos)
        for key in (f"{mc_version}-recommended", f"{mc_version}-latest"):
            value = promo.get(key)
            if value:
                log(f"Forge {value} ({key}) para Minecraft {mc_version}")
                return str(value)
    except Exception as error:  # noqa: BLE001
        log(f"No se pudieron leer las promociones de Forge: {error}")
    raise RuntimeError(
        f"No hay build de Forge publicado para Minecraft {mc_version}")


def _download(url: str, target: Path, log=print) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size > 0:
        return target
    log(f"Descargando {url.rsplit('/', 1)[-1]}…")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response, \
            target.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = response.read(262144)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                log(f"  {human_size(done)} / {human_size(total)}")
    log(f"Descarga completa ({human_size(target.stat().st_size)})")
    return target


def installed_profiles() -> list[str]:
    """Perfiles forge-* ya instalados en cualquier raiz .minecraft."""
    found = []
    for versions_dir in paths.versions_dirs():
        try:
            children = sorted(versions_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if (child.is_dir() and "forge" in child.name.lower()
                    and (child / f"{child.name}.json").exists()):
                found.append(child.name)
    return found


def _find_forge_profile(mc_version: str) -> str | None:
    """Busca el perfil forge-* creado por el instalador en versions/.

    Con varios Forge instalados (una por version de MC) se prefiere el que
    declara ``inheritsFrom == mc_version``; si ninguno coincide, se usa el
    primero como respaldo para no romper el flujo.
    """
    fallback = None
    for versions_dir in paths.versions_dirs():
        try:
            children = sorted(versions_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or "forge" not in child.name.lower():
                continue
            payload = load_version_profile(child.name)
            if payload is None:
                continue
            if fallback is None:
                fallback = child.name
            if payload.get("inheritsFrom") == mc_version \
                    or child.name.startswith(mc_version):
                return child.name
    return fallback


def _profile_from_installer(installer: Path) -> str | None:
    """Crea el perfil Forge directamente desde install_profile.json.

    Los instaladores de Forge empaquetan la definicion completa de la
    version (versionInfo + inheritsFrom + librerias). Si no hay
    processors/binarios que ejecutar, escribir el perfil es equivalente
    a instalar — sin ventanas y sin Java extra.
    Devuelve el id del perfil creado o None si no es posible.
    """
    try:
        with zipfile.ZipFile(installer) as jar:
            if "install_profile.json" not in jar.namelist():
                return None
            profile = json.loads(
                jar.read("install_profile.json").decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    if profile.get("processors") or profile.get("binaries"):
        return None
    info = profile.get("install") or {}
    version_info = profile.get("versionInfo")
    target = info.get("target")
    if not version_info or not target:
        return None

    # El artefacto principal de Forge es el "universal"; el nombre maven
    # del versionInfo no lleva clasificador y resolveria a un jar 404.
    file_path = info.get("filePath") or ""
    classifier = ""
    if file_path.endswith(".jar"):
        stem = file_path[:-4].rsplit("-", 1)
        if len(stem) == 2 and stem[1] in ("universal", "client", "slim"):
            classifier = stem[1]
    for library in version_info.get("libraries") or []:
        name = library.get("name", "")
        if (classifier and name.count(":") == 2
                and name.startswith("net.minecraftforge:forge:")):
            library["name"] = f"{name}:{classifier}"

    version_info.setdefault("id", target)
    write_version_profile(target, version_info)
    return target


def _ensure_launcher_profiles(mc_version: str) -> None:
    """Crea un launcher_profiles.json minimo si falta.

    El instalador de Forge lo exige incluso en modo --installClient y
    aborta con 'there is no minecraft launcher profile' cuando el usuario
    nunca ha ejecutado el launcher oficial.
    """
    target = paths.MC_DIR / "launcher_profiles.json"
    if target.exists():
        return
    import uuid as _uuid
    payload = {"profiles": {
        _uuid.uuid4().hex: {
            "name": mc_version,
            "type": "custom",
            "lastVersionId": mc_version,
            "icon": "Grass",
        },
    }}
    try:
        target.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def install_forge(mc_version: str, java_path: str = "", log=print) -> str:
    """Instala Forge en segundo plano y devuelve la version instalada.

    Usa el modo headless del instalador oficial (--installClient). Si la
    version de Forge no lo soporta, abre el instalador grafico como
    respaldo para que el usuario complete la instalacion.
    """
    # El instalador de Forge necesita el perfil vanilla de esa version
    # como base; sin el falla con un error poco claro. Se acepta el json
    # en cualquier raiz .minecraft registrada.
    if paths.find_version_json(mc_version) is None:
        raise RuntimeError(
            f"Instala primero Minecraft {mc_version} desde la pestana "
            "Versiones: Forge necesita su perfil base.")

    forge_version = latest_forge_version(mc_version, log)
    # En el maven de Forge la version completa incluye el prefijo de MC:
    # 1.12.2-14.23.5.2859 (las promociones solo devuelven el build).
    full_version = f"{mc_version}-{forge_version}"
    jar_name = f"forge-{full_version}-installer.jar"
    url = f"{_MAVEN_DL}/{full_version}/{jar_name}"
    installer = _download(url, paths.CACHE_DIR / "forge" / jar_name, log)

    log(f"Instalando Forge {forge_version} para Minecraft {mc_version}…")
    _ensure_launcher_profiles(mc_version)

    # Via 1 (100% silenciosa): escribir el perfil desde install_profile.json.
    profile = _profile_from_installer(installer)
    if profile:
        log(f"Forge instalado sin ventanas: perfil '{profile}' listo "
            "en Versiones.")
        return forge_version

    runtime = select_runtime(8, java_path)
    if runtime is None:
        raise RuntimeError(
            "No se encontro Java 8+ para ejecutar el instalador de Forge. "
            "Activa 'descargar Java automaticamente' en Ajustes.")

    # Via 2: modo headless del instalador oficial (--installClient).
    try:
        result = subprocess.run(
            [str(runtime.java), "-jar", str(installer),
             "--installClient", str(paths.MC_DIR)],
            cwd=str(paths.MC_DIR), capture_output=True, text=True,
            timeout=600, check=False)
    except subprocess.TimeoutExpired:
        result = None
    if result is not None and result.returncode == 0:
        profile = _find_forge_profile(mc_version)
        if profile:
            log(f"Forge instalado: perfil '{profile}' disponible en "
                "Versiones.")
            return forge_version
        log("El instalador termino pero no se encontro el perfil; "
            "revisando de nuevo…")
    else:
        tail = ""
        if result is not None:
            tail = (result.stderr or result.stdout or "").strip()[-400:]
        log(f"La instalacion silenciosa no esta disponible para esta "
            f"version de Forge{': ' + tail if tail else '.'}")

    # Respaldo: abrir el instalador grafico oficial.
    java = runtime.javaw if runtime.javaw.exists() else runtime.java
    log("Abriendo el instalador grafico de Forge…")
    subprocess.Popen([str(java), "-jar", str(installer)],
                     cwd=str(paths.MC_DIR))
    return forge_version
