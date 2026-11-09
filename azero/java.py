"""Gestion del runtime de Java: deteccion local y descarga de Microsoft OpenJDK."""

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
from .constants import MICROSOFT_JDK_URL
from .util import (DownloadTask, download_many, extract_archive,
                   human_size, open_url)


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


def _version_sort_key(version: str) -> tuple[int, ...]:
    """Clave de orden para '21.0.13+9' / '1.8.0_504' -> tupla numerica."""
    numbers = [int(part) for part in re.findall(r"\d+", version)[:4]]
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers)


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
    # Mayor primero; a igual major, el parche mas reciente (los JDK de
    # Microsoft se instalan como microsoft-jdk-<major>-<version>).
    return sorted(runtimes.values(),
                  key=lambda item: (item.major, _version_sort_key(item.version)),
                  reverse=True)


def manual_runtime(java_path: str) -> JavaRuntime | None:
    if not java_path:
        return None
    path = Path(java_path).expanduser()
    java_name = "java.exe" if sys.platform.startswith("win") else "java"
    if path.is_file():
        home = path.parent.parent
    elif path.is_dir():
        home = path
        # El usuario puede señalar la carpeta bin/ o el JDK raiz; ambas
        # deben resolver al home que contiene bin/java.
        if not (home / "bin" / java_name).exists() \
                and (home / java_name).exists():
            home = home.parent
    else:
        return None
    return _runtime_from_home(home, "manual")


# Java 16 introdujo la encapsulacion fuerte de modulos (JEP 396): los
# nativos LWJGL2 de Minecraft <= 1.12.2 fallan con IllegalAccessError.
# Por eso el objetivo "legacy" (11) admite como maximo Java 15.
_LEGACY_JAVA_MAX = 15
# Para objetivos 17+ se acepta cualquier LTS igual o mas reciente
# razonable; mas alla de eso el perfil oficial manda.
_MODERN_JAVA_MAX = 21


def _major_compatible(major: int, required: int,
                      max_major: int = 0) -> bool:
    """Compatibilidad practica entre el Java instalado y el objetivo.

    El objetivo ya es el LTS moderno elegido por `preferred_java_major`:
    legacy (8-11) admite 8-15, 17 admite 17-21, y 21/25 admiten cualquier
    major igual o posterior. `max_major` permite ampliar el techo (los
    instaladores de loaders no son el juego y toleran Java mas reciente).
    """
    ceiling = max_major or 0
    if required <= 11:
        return 8 <= major <= (ceiling or _LEGACY_JAVA_MAX)
    if required <= 17:
        return required <= major <= (ceiling or _MODERN_JAVA_MAX)
    return major >= required


def _major_rank(major: int, required: int,
                prefer_newest: bool = True) -> tuple[int, int, int]:
    """Orden de preferencia entre runtimes compatibles.

    Para el juego (`prefer_newest`) gana el major exacto y luego el mas
    nuevo dentro de la ventana; para instaladores de loaders conviene el
    mas cercano al declarado, no el mas nuevo posible.
    """
    if prefer_newest:
        return (major != required, -major, major)
    return (major != required, abs(major - required), -major)


def select_runtime(major: int, java_path: str = "",
                   max_major: int = 0,
                   prefer_newest: bool = True) -> JavaRuntime | None:
    manual = manual_runtime(java_path)
    if manual and _major_compatible(manual.major, major, max_major):
        return manual

    runtimes = [item for item in find_runtimes()
                if _major_compatible(item.major, major, max_major)]
    if not runtimes:
        return None
    return min(runtimes,
               key=lambda item: _major_rank(item.major, major,
                                            prefer_newest))


def _jdk_platform() -> str:
    """Plataforma para las URLs oficiales de Microsoft OpenJDK."""
    machine = platform.machine().lower()
    arch = "aarch64" if machine in ("arm64", "aarch64") else "x64"
    if sys.platform.startswith("win"):
        return f"windows-{arch}.zip"
    if sys.platform == "darwin":
        return f"macOS-{arch}.tar.gz"
    return f"linux-{arch}.tar.gz"


def _microsoft_jdk_url(major: int) -> str:
    return MICROSOFT_JDK_URL.format(major=major,
                                    platform=_jdk_platform())


def _jdk_package_info(url: str) -> tuple[int | None, str]:
    """Tamano y version real del paquete via headers (sin descargar)."""
    size: int | None = None
    release = ""
    try:
        with open_url(url, timeout=30) as response:
            length = response.headers.get("Content-Length")
            if length and length.isdigit():
                size = int(length)
            disposition = response.headers.get("Content-Disposition", "")
            match = re.search(r"microsoft-jdk-([0-9]+\.[0-9.]+)",
                              disposition)
            if match:
                release = match.group(1)
    except Exception:  # noqa: BLE001 - los headers son best-effort
        pass
    return size, release


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
    """Descarga Microsoft Build of OpenJDK (LTS) y lo extrae.

    Usa las URLs oficiales por major (aka.ms/download-jdk) que siempre
    apuntan al ultimo parche de ese LTS: Java 11, 17, 21 y 25.
    """
    paths.ensure_dirs()
    url = _microsoft_jdk_url(major)
    size, release = _jdk_package_info(url)
    if not release:
        release = str(major)

    downloads_dir = paths.JAVA_DIR / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    archive_ext = ".zip" if url.endswith(".zip") else ".tar.gz"
    archive = downloads_dir / (f"microsoft-jdk-{major}-{release}"
                               f"{archive_ext}")
    log(f"Descargando Microsoft OpenJDK {major}"
        + (f" ({human_size(size)})" if size else ""))

    download_many(
        [DownloadTask(
            url=url,
            dest=archive,
            size=size,
            label=f"Microsoft OpenJDK {major}",
        )],
        on_progress=progress, workers=1, cancel=cancel, log=log,
    )

    stage(f"Instalando Java {major}")
    target = paths.JAVA_DIR / f"microsoft-jdk-{major}-{release}"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    extract_archive(archive, target)
    archive.unlink(missing_ok=True)  # el paquete pesa ~200 MB: no conservarlo
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
    manual = manual_runtime(java_path)
    if manual is not None and not _major_compatible(manual.major, major):
        log(f"El Java configurado en Ajustes ({manual.version or manual.major}) "
            f"no es compatible con esta version (requiere Java {major}+); "
            "se usara otro runtime detectado.")
    runtime = select_runtime(major, java_path)
    if runtime:
        return runtime
    if not allow_download:
        raise JavaNotFound(
            f"No se encontro Java {major}. Instala un Java {major} o activa "
            "la descarga automatica en Ajustes."
        )
    stage(f"Descargando Java {major} (no instalado)")
    return download_java(major, progress, stage, log, cancel)
