"""Instalacion de OptiFine a partir de su instalador oficial, sin GUI."""

from __future__ import annotations

import re
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

from . import java as java_module
from . import paths
from .install import TaskContext, prepare
from .manifest import load_version_profile, write_version_profile
from .util import write_json

# Versiones de MC aceptadas: clasicas (1.12.2), pre-releases (1.21-pre3),
# snapshots de calendario (26.4-snapshot-7) y semanales (23w13a). La
# release de OptiFine puede llevar guiones bajos (HD_U_J1_pre9).
_MC_VERSION = (r"(?:\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z]+)*"
               r"|\d{2}w\d{1,2}[a-z]?)")
_SUFFIX = r"([A-Za-z0-9_]+)"

# changelog.txt embebido: primera linea "OptiFine 1.20.1_HD_U_I6".
# Es la fuente mas fiable: no depende del nombre del archivo.
_CHANGELOG_RE = re.compile(
    rf"OptiFine\s+({_MC_VERSION})_{_SUFFIX}", re.IGNORECASE)
# Nombre de archivo: OptiFine_1.20.1_HD_U_I6.jar (busca en cualquier parte
# del nombre por si el usuario lo renombro o el navegador anadio sufijos).
_FILENAME_RE = re.compile(
    rf"OptiFine\D*({_MC_VERSION})_{_SUFFIX}", re.IGNORECASE)
_VERSION_PREFIX_RE = re.compile(
    rf"^\s*({_MC_VERSION})_{_SUFFIX}",
)
_IMPLEMENTATION_RE = re.compile(r"Implementation-Version:\s*(.+)", re.IGNORECASE)
_CONFIG_ENTRIES = (
    "net/optifine/Config.class",
    "Config.class",
    "notch/net/optifine/Config.class",
    "srg/net/optifine/Config.class",
)
LAUNCHWRAPPER_FALLBACK = "net.minecraft:launchwrapper:1.12"


class OptiFineError(RuntimeError):
    pass


@dataclass
class OptiFineInfo:
    mc_version: str
    edition: str
    release: str
    edition_release: str
    launchwrapper: str | None
    profile_id: str

    @property
    def display(self) -> str:
        return f"OptiFine {self.mc_version} {self.edition_release}"


def _split_edition_release(suffix: str) -> tuple[str, str]:
    """Separa 'HD_U_G5' -> ('HD_U', 'G5'); 'HD_U_J1_pre9' -> ('HD_U', 'J1_pre9').

    La edition es siempre 'HD_U' (o 'HD_L' en versiones muy antiguas);
    el resto es la release, que puede contener guiones bajos.
    """
    parts = suffix.split("_")
    if len(parts) >= 3 and parts[0] == "HD":
        return "_".join(parts[:2]), "_".join(parts[2:])
    if len(parts) >= 2:
        return parts[0], "_".join(parts[1:])
    return suffix, ""


def _version_from_match(match: re.Match) -> tuple[str, str, str]:
    edition, release = _split_edition_release(match.group(2))
    return match.group(1), edition, release


def _parse_version_string(raw: str) -> tuple[str, str, str] | None:
    match = _VERSION_PREFIX_RE.match(raw)
    if not match:
        return None
    return _version_from_match(match)


def _detect_version(archive: zipfile.ZipFile,
                    installer_name: str) -> tuple[str, str, str] | None:
    """Detecta (mc_version, edition, release) con varias fuentes.

    Orden: changelog.txt embebido (siempre presente en instaladores
    oficiales), nombre del archivo (por si el usuario lo renombro) y
    META-INF/MANIFEST.MF Implementation-Version (instaladores antiguos).
    """
    names = set(archive.namelist())

    if "changelog.txt" in names:
        try:
            head = archive.read("changelog.txt").decode(
                "utf-8", errors="ignore").splitlines()[:10]
        except (KeyError, OSError):
            head = []
        for line in head:
            match = _CHANGELOG_RE.search(line.strip())
            if match:
                return _version_from_match(match)

    match = _FILENAME_RE.search(installer_name)
    if match:
        return _version_from_match(match)

    if "META-INF/MANIFEST.MF" in names:
        try:
            manifest_text = archive.read("META-INF/MANIFEST.MF").decode(
                "utf-8", errors="ignore")
        except (KeyError, OSError):
            manifest_text = ""
        match = _IMPLEMENTATION_RE.search(manifest_text)
        if match:
            return _parse_version_string(match.group(1))

    return None


def inspect_installer(installer: Path) -> OptiFineInfo:
    if not installer.exists():
        raise OptiFineError(f"No existe el archivo: {installer}")
    if not zipfile.is_zipfile(installer):
        raise OptiFineError("El archivo seleccionado no es un instalador de OptiFine.")

    with zipfile.ZipFile(installer) as archive:
        names = set(archive.namelist())
        if not any(entry in names for entry in _CONFIG_ENTRIES):
            raise OptiFineError(
                "El jar no contiene las clases de OptiFine. Descarga el instalador "
                "oficial desde optifine.net."
            )

        launchwrapper = None
        if "launchwrapper-of.txt" in names:
            launchwrapper = archive.read("launchwrapper-of.txt").decode(
                "utf-8", errors="ignore"
            ).strip() or None

        parsed = _detect_version(archive, installer.name)

    if parsed is None:
        raise OptiFineError(
            "No se pudo determinar la version de OptiFine. El archivo no "
            "parece un instalador oficial completo; descargalo de nuevo "
            "desde optifine.net."
        )

    mc_version, edition, release = parsed
    edition_release = f"{edition}_{release}" if release else edition
    return OptiFineInfo(
        mc_version=mc_version,
        edition=edition,
        release=release,
        edition_release=edition_release,
        launchwrapper=launchwrapper,
        profile_id=f"{mc_version}-OptiFine_{edition_release}",
    )


def _launchwrapper_jar(installer: Path, version: str) -> Path:
    dest = (paths.LIBRARIES_DIR / "optifine" / "launchwrapper-of" / version
            / f"launchwrapper-of-{version}.jar")
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    with zipfile.ZipFile(installer) as archive:
        entry = f"launchwrapper-of-{version}.jar"
        if entry not in archive.namelist():
            raise OptiFineError(
                "El instalador no incluye launchwrapper; se usara el de Mojang."
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(archive.read(entry))
    return dest


def _run_patcher(runtime: java_module.JavaRuntime, installer: Path,
                 client_jar: Path, dest: Path, log) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(runtime.java), "-cp", str(installer), "optifine.Patcher",
        str(client_jar), str(installer), str(dest),
    ]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
    log("Aplicando parche de OptiFine al cliente...")
    try:
        completed = subprocess.run(
            command, cwd=str(paths.MC_DIR), capture_output=True, text=True,
            timeout=600, creationflags=flags,
        )
    except subprocess.TimeoutExpired as error:
        raise OptiFineError("OptiFine tardo demasiado en parchear el cliente.") from error
    except OSError as error:
        raise OptiFineError(f"No se pudo ejecutar el parcheador: {error}") from error

    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if completed.returncode != 0 or not dest.exists() or dest.stat().st_size == 0:
        tail = output[-1200:] if output else "sin salida"
        raise OptiFineError(
            f"OptiFine no pudo aplicar el parche (codigo {completed.returncode}).\n{tail}"
        )


def _profile_payload(info: OptiFineInfo) -> dict:
    libraries = []
    if info.launchwrapper:
        libraries.append({"name": f"optifine:launchwrapper-of:{info.launchwrapper}"})
    else:
        libraries.append({"name": LAUNCHWRAPPER_FALLBACK})
    libraries.append({
        "name": f"optifine:Optifine:{info.mc_version}_{info.edition_release}"
    })
    now = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    return {
        "id": info.profile_id,
        "inheritsFrom": info.mc_version,
        "type": "release",
        "mainClass": "net.minecraft.launchwrapper.Launch",
        "arguments": {
            "game": ["--tweakClass", "optifine.OptiFineTweaker"],
            "jvm": [],
        },
        "libraries": libraries,
        "minimumLauncherVersion": 21,
        "time": now,
        "releaseTime": now,
    }


def install_optifine(installer: Path, base_version: str, settings,
                     ctx: TaskContext) -> OptiFineInfo:
    """Prepara la version base, parchea el cliente y registra el perfil."""
    info = inspect_installer(installer)
    if info.mc_version != base_version:
        raise OptiFineError(
            f"Este OptiFine es para {info.mc_version}, pero seleccionaste "
            f"{base_version}. Elige la version correspondiente."
        )

    existing = load_version_profile(info.profile_id)
    if existing and (paths.LIBRARIES_DIR / "optifine" / "Optifine"
                     / f"{info.mc_version}_{info.edition_release}"
                     / f"Optifine-{info.mc_version}_{info.edition_release}.jar").exists():
        ctx.log(f"{info.display} ya estaba instalado.")
        return info

    offline = bool(getattr(settings, "offline_mode", False))
    ctx.stage(f"Preparando Minecraft {base_version}")
    prepared = prepare(base_version, ctx, with_assets=False,
                       offline=offline)
    ctx.check()

    runtime = java_module.ensure_java(
        prepared.java_major,
        java_path=settings.java_path,
        allow_download=settings.auto_download_java and not offline,
        progress=ctx.progress,
        stage=ctx.stage,
        log=ctx.log,
        cancel=ctx.cancel_event.is_set,
    )

    ctx.stage(f"Instalando {info.display}")
    dest = (paths.LIBRARIES_DIR / "optifine" / "Optifine"
            / f"{info.mc_version}_{info.edition_release}"
            / f"Optifine-{info.mc_version}_{info.edition_release}.jar")
    # El cliente puede vivir en otra raiz .minecraft registrada; prepare()
    # lo reutiliza sin descargarlo a la oficial, asi que hay que apuntar
    # al jar real o el parcheador fallaria con "file not found".
    client_jar = (paths.find_version_jar(base_version)
                  or paths.version_jar_path(base_version))
    _run_patcher(runtime, installer, client_jar, dest, ctx.log)
    ctx.check()

    if info.launchwrapper:
        try:
            _launchwrapper_jar(installer, info.launchwrapper)
        except OptiFineError as error:
            ctx.log(str(error))

    write_version_profile(info.profile_id, _profile_payload(info))
    write_json(paths.CACHE_DIR / "optifine.json", {
        "profile_id": info.profile_id,
        "mc_version": info.mc_version,
        "edition_release": info.edition_release,
    })
    ctx.log(f"Perfil creado: {info.profile_id}")
    return info
