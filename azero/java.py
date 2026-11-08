"""Gestion del runtime de Java: deteccion local y descarga de Temurin."""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from . import paths
from .constants import ADOPTIUM_ASSET_URL
from .util import DownloadTask, download_many, extract_zip, fetch_json, human_size


class JavaNotFound(RuntimeError):
    pass


@dataclass
class JavaRuntime:
    home: Path
    major: int
    version: str
    source: str

    @property
    def java(self) -> Path:
        executable = "javaw.exe" if sys.platform.startswith("win") else "java"
        candidate = self.home / "bin" / executable
        if candidate.exists():
            return candidate
        return self.home / "bin" / ("java.exe" if sys.platform.startswith("win") else "java")

    @property
    def javaw(self) -> Path:
        if sys.platform.startswith("win"):
            candidate = self.home / "bin" / "javaw.exe"
            if candidate.exists():
                return candidate
        return self.java

    @property
    def label(self) -> str:
        return f"Java {self.major} ({self.version})"


def _major_from_version(raw: str) -> int:
    raw = raw.strip().strip('"')
    if raw.startswith("1."):
        match = re.match(r"1\.(\d+)", raw)
        return int(match.group(1)) if match else 0
    match = re.match(r"(\d+)", raw)
    return int(match.group(1)) if match else 0


def _runtime_from_home(home: Path, source: str) -> JavaRuntime | None:
    if not home:
        return None
    java_name = "java.exe" if sys.platform.startswith("win") else "java"
    binary = home / "bin" / java_name
    if not binary.exists():
        return None

    version = ""
    release = home / "release"
    if release.exists():
        try:
            for line in release.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("JAVA_VERSION="):
                    version = line.split("=", 1)[1].strip().strip('"')
                    break
        except OSError:
            version = ""

    major = _major_from_version(version)
    if major == 0:
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
            completed = subprocess.run(
                [str(binary), "-version"],
                capture_output=True, text=True, timeout=12, creationflags=flags,
            )
            output = (completed.stderr or "") + (completed.stdout or "")
            match = re.search(r'version "([^"]+)"', output)
            if match:
                version = match.group(1)
                major = _major_from_version(version)
        except (OSError, subprocess.SubprocessError):
            return None
    if major <= 0:
        return None
    return JavaRuntime(home=home, major=major, version=version, source=source)


def _candidate_homes() -> list[tuple[Path, str]]:
    candidates: list[tuple[Path, str]] = []

    if paths.JAVA_DIR.exists():
        for child in sorted(paths.JAVA_DIR.iterdir()):
            if child.is_dir() and child.name != "downloads":
                home = _find_java_home(child)
                if home:
                    candidates.append((home, "AZeroCraft"))

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidates.append((Path(java_home), "JAVA_HOME"))

    if sys.platform.startswith("win"):
        program_files = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                         os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        vendors = ("Java", "Eclipse Adoptium", "Eclipse Foundation", "Microsoft",
                   "Zulu", "BellSoft", "Semeru", "Amazon Corretto", "OpenJDK")
        for base in program_files:
            for vendor in vendors:
                vendor_dir = Path(base) / vendor
                if vendor_dir.is_dir():
                    for child in vendor_dir.iterdir():
                        if child.is_dir():
                            candidates.append((child, vendor))
                    candidates.append((vendor_dir, vendor))
    else:
        for base in ("/usr/lib/jvm", "/Library/Java/JavaVirtualMachines"):
            base_path = Path(base)
            if base_path.is_dir():
                for child in base_path.iterdir():
                    candidates.append((child, "sistema"))
                    candidates.append((child / "Contents" / "Home", "sistema"))

    which_java = shutil.which("java")
    if which_java:
        candidates.append((Path(which_java).resolve().parent.parent, "PATH"))

    return candidates


def find_runtimes() -> list[JavaRuntime]:
    runtimes: dict[str, JavaRuntime] = {}
    for home, source in _candidate_homes():
        try:
            runtime = _runtime_from_home(home, source)
        except Exception:  # noqa: BLE001 - un JRE roto no debe romper el escaneo
            runtime = None
        if runtime:
            key = str(runtime.java).lower()
            if key not in runtimes or runtimes[key].source == "PATH":
                runtimes[key] = runtime
    return sorted(runtimes.values(), key=lambda item: item.major, reverse=True)


def manual_runtime(java_path: str) -> JavaRuntime | None:
    if not java_path:
        return None
    path = Path(java_path).expanduser()
    if path.is_file():
        home = path.parent.parent
    elif path.is_dir():
        home = path
    else:
        return None
    return _runtime_from_home(home, "manual")


def _major_compatible(major: int, required: int) -> bool:
    """Compatibilidad practica entre el Java instalado y el que pide el perfil.

    Minecraft <= 1.16.5 (javaVersion 8) funciona con Java 8-16, pero no con
    17+ por el encapsulamiento de modulos. Las versiones nuevas aceptan un
    Java igual o mas reciente.
    """
    if required <= 8:
        return 8 <= major <= 16
    return major >= required


def _major_rank(major: int, required: int) -> tuple[int, int]:
    """Orden de preferencia: primero el major exacto, luego el mas cercano."""
    return (major != required, abs(major - required), major)


def select_runtime(major: int, java_path: str = "") -> JavaRuntime | None:
    manual = manual_runtime(java_path)
    if manual and _major_compatible(manual.major, major):
        return manual

    runtimes = [item for item in find_runtimes()
                if _major_compatible(item.major, major)]
    if not runtimes:
        return None
    return min(runtimes, key=lambda item: _major_rank(item.major, major))


def _adoptium_arch() -> str:
    machine = platform.machine().lower()
    if machine in ("arm64", "aarch64"):
        return "aarch64"
    return "x64"


def _adoptium_os() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def _find_java_home(root: Path) -> Path | None:
    executable = "java.exe" if sys.platform.startswith("win") else "java"
    try:
        direct = root / "bin" / executable
        if direct.exists():
            return root
        children = sorted(root.iterdir())
    except OSError:
        return None
    for child in children:
        if child.is_dir():
            found = _find_java_home(child)
            if found:
                return found
    return None


def download_java(major: int, progress: Callable[[int, int], None],
                  stage: Callable[[str], None], log: Callable[[str], None],
                  cancel: Callable[[], bool] | None = None) -> JavaRuntime:
    """Descarga Temurin (JRE) desde la API de Adoptium y lo extrae."""
    paths.ensure_dirs()
    api_url = ADOPTIUM_ASSET_URL.format(
        major=major, arch=_adoptium_arch(), os=_adoptium_os()
    )
    payload = fetch_json(api_url)
    if not payload:
        # Algunos majors (p. ej. 8) no publican JRE separado: reintentar
        # sin el filtro image_type=jre para aceptar el JDK completo.
        fallback = ADOPTIUM_ASSET_URL.format(
            major=major, arch=_adoptium_arch(), os=_adoptium_os()
        ).replace("&image_type=jre", "")
        payload = fetch_json(fallback)
    if not payload:
        raise JavaNotFound(f"No hay builds de Java {major} disponibles para este sistema.")
    asset = payload[0]
    package = asset["binary"]["package"]
    release = asset.get("release_name", str(major))

    downloads_dir = paths.JAVA_DIR / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    archive = downloads_dir / package["name"]
    log(f"Descargando {package['name']} ({human_size(package.get('size', 0))})")

    download_many(
        [DownloadTask(
            url=package["link"],
            dest=archive,
            sha256=package.get("checksum"),
            size=package.get("size"),
            label=package["name"],
        )],
        on_progress=progress, workers=1, cancel=cancel, log=log,
    )

    stage(f"Instalando Java {major}")
    target = paths.JAVA_DIR / f"temurin-{major}-{release}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    extract_zip(archive, target)
    home = _find_java_home(target)
    if home is None:
        raise JavaNotFound("El paquete de Java descargado no contiene un binario valido.")
    runtime = _runtime_from_home(home, "AZeroCraft")
    if runtime is None:
        raise JavaNotFound("No se pudo validar el Java descargado.")
    log(f"Java {runtime.major} instalado en {runtime.home}")
    return runtime


def ensure_java(major: int, java_path: str = "", allow_download: bool = True,
                progress: Callable[[int, int], None] = lambda done, total: None,
                stage: Callable[[str], None] = lambda text: None,
                log: Callable[[str], None] = lambda text: None,
                cancel: Callable[[], bool] | None = None) -> JavaRuntime:
    runtime = select_runtime(major, java_path)
    if runtime:
        return runtime
    if not allow_download:
        raise JavaNotFound(
            f"No se encontro Java {major}. Instala un JRE {major} o activa la "
            "descarga automatica en Ajustes."
        )
    stage(f"Descargando Java {major} (no instalado)")
    return download_java(major, progress, stage, log, cancel)
