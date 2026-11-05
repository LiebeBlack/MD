"""Resolucion de librerias, classpath y extraccion de nativos."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .constants import LIBRARIES_URL
from .rules import default_features, os_arch, os_name, rules_allow
from .util import DownloadTask, extract_zip

_NATIVE_CLASSIFIER = re.compile(r":natives-[A-Za-z0-9_-]+$")


@dataclass
class LibraryPlan:
    downloads: list[DownloadTask] = field(default_factory=list)
    classpath: list[Path] = field(default_factory=list)
    natives: list[tuple[Path, tuple[str, ...]]] = field(default_factory=list)


def maven_path(name: str) -> str:
    """Convierte group:artifact:version[:classifier] en su ruta maven."""
    parts = name.split(":")
    if len(parts) < 3:
        raise ValueError(f"Coordenada maven invalida: {name}")
    group, artifact, version = parts[0], parts[1], parts[2]
    classifier = parts[3] if len(parts) > 3 else None
    filename = f"{artifact}-{version}" + (f"-{classifier}" if classifier else "") + ".jar"
    return "/".join((*group.split("."), artifact, version, filename))


def _synthesized_download(library: dict) -> DownloadTask | None:
    """Librerias sin bloque downloads (perfiles OptiFine/Forge)."""
    name = library.get("name")
    if not name:
        return None
    try:
        relative = maven_path(name)
    except ValueError:
        return None
    base_url = library.get("url") or LIBRARIES_URL
    if not base_url.endswith("/"):
        base_url += "/"
    dest = paths.LIBRARIES_DIR / relative
    return DownloadTask(url=base_url + relative, dest=dest, label=name)


def build_library_plan(version_json: dict, features: dict[str, bool] | None = None,
                       include_natives: bool = True) -> LibraryPlan:
    features = features or default_features()
    plan = LibraryPlan()
    seen_classpath: set[str] = set()

    for library in version_json.get("libraries", []):
        if not rules_allow(library.get("rules"), features):
            continue

        name = library.get("name", "")
        downloads = library.get("downloads") or {}
        artifact = downloads.get("artifact")
        is_native_classifier = bool(_NATIVE_CLASSIFIER.search(name))
        natives_map = library.get("natives") or {}

        if artifact and artifact.get("url"):
            task = DownloadTask(
                url=artifact["url"],
                dest=paths.LIBRARIES_DIR / artifact["path"],
                sha1=artifact.get("sha1"),
                size=artifact.get("size"),
                label=name,
            )
            plan.downloads.append(task)
            artifact_path = task.dest
        else:
            artifact_path = None
            # Las librerias solo-nativas (jinput-platform, twitch-platform...)
            # no tienen jar base: no existe nada que descargar ni poner en -cp.
            if not natives_map and not is_native_classifier:
                task = _synthesized_download(library)
                artifact_path = task.dest if task else None
                # Los artefactos de OptiFine solo existen si los creo su
                # instalador; nunca se descargan de un repositorio remoto.
                if (task and not task.dest.exists()
                        and not name.startswith("optifine:")):
                    plan.downloads.append(task)

        if artifact_path and not is_native_classifier:
            key = str(artifact_path).lower()
            if key not in seen_classpath:
                seen_classpath.add(key)
                plan.classpath.append(artifact_path)

        # Nativos con mapa "natives" (formato clasico, 1.8 - 1.12)
        classifier = _resolve_classifier(natives_map)
        if classifier and include_natives:
            classifier_download = (downloads.get("classifiers") or {}).get(classifier)
            if classifier_download:
                dest = paths.LIBRARIES_DIR / classifier_download["path"]
                plan.downloads.append(DownloadTask(
                    url=classifier_download["url"],
                    dest=dest,
                    sha1=classifier_download.get("sha1"),
                    size=classifier_download.get("size"),
                    label=f"{name}:{classifier}",
                ))
                excludes = tuple(
                    (library.get("extract") or {}).get("exclude") or ("META-INF/",)
                )
                plan.natives.append((dest, excludes))

        # Nativos empaquetados como libreria con clasificador (1.13+)
        if is_native_classifier and include_natives and artifact_path:
            excludes = tuple((library.get("extract") or {}).get("exclude") or ("META-INF/",))
            plan.natives.append((artifact_path, excludes))

    return plan


def _resolve_classifier(natives_map: dict) -> str | None:
    """Resuelve el clasificador de nativos, incluido el marcador ${arch}."""
    classifier = natives_map.get(os_name())
    if not classifier:
        return None
    arch = "32" if os_arch() == "x86" else "64"
    return classifier.replace("${arch}", arch)


def extract_natives(plan: LibraryPlan, target: Path, log=None) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for existing in target.iterdir():
        if existing.is_file() and existing.suffix.lower() in (".dll", ".so", ".dylib", ".jnilib"):
            existing.unlink(missing_ok=True)
    for archive, excludes in plan.natives:
        if not archive.exists():
            continue
        extract_zip(archive, target, excludes=excludes)
    if log:
        log(f"Nativos extraidos en {target}")
