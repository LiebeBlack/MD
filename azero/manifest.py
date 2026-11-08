"""Manifiestos oficiales de Minecraft: listado, version.json y herencia."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from . import paths
from .constants import (MAX_VERSION, MIN_VERSION, VERSION_MANIFEST_URL)
from .util import fetch_json, read_json, write_json

MANIFEST_TTL_SECONDS = 6 * 3600


# Snapshots semanales antiguos: 23w13a, 25w31a...
_WEEKLY_SNAPSHOT = re.compile(r"^(\d{2})w(\d{1,2})([a-zA-Z])?$")
# Versiones con sufijo (-snapshot-N, -preN, -OptiFine_...): el prefijo
# numerado define el orden; los empates conservan el orden del manifiesto.
_NUMERIC_PREFIX = re.compile(r"^(\d+(?:\.\d+){0,3})")


def _version_key(version_id: str) -> tuple[int, int, int] | None:
    if not version_id:
        return None
    weekly = _WEEKLY_SNAPSHOT.match(version_id)
    if weekly:
        year, week = int(weekly.group(1)), int(weekly.group(2))
        letter = weekly.group(3)
        patch = ord(letter.lower()) - 96 if letter else 0
        return year, week, patch
    match = _NUMERIC_PREFIX.match(version_id)
    if not match:
        return None
    numbers = [int(part) for part in match.group(1).split(".")]
    while len(numbers) < 3:
        numbers.append(0)
    return tuple(numbers[:3])  # type: ignore[return-value]


def in_supported_range(version_id: str) -> bool:
    key = _version_key(version_id)
    if key is None:
        return False
    return MIN_VERSION <= key <= MAX_VERSION


def parse_version_key(version_id: str) -> tuple[int, int, int]:
    return _version_key(version_id) or (0, 0, 0)


def version_family_label(version_id: str) -> str:
    """Etiqueta de familia para agrupar versiones en la UI.

    Releases clasicas se agrupan por major.minor (1.12.x, 1.21.x) y los
    snapshots semanales por año (23w). Desde el versionado de calendario
    de Mojang (26.x en adelante) todo el año forma una sola familia.
    """
    weekly = _WEEKLY_SNAPSHOT.match(version_id)
    if weekly:
        return f"{weekly.group(1)}w"
    key = parse_version_key(version_id)
    if key == (0, 0, 0):
        return "Otras"
    if key[0] >= 26:
        return f"{key[0]}.x"
    return f"{key[0]}.{key[1]}.x"


def fetch_manifest(force: bool = False,
                   offline: bool = False) -> dict:
    """Descarga (con cache de 6 h) el version_manifest_v2 oficial.

    Con ``offline=True`` nunca toca la red: devuelve la cache local o
    un manifiesto vacio para que los perfiles locales sigan funcionando.
    """
    paths.ensure_dirs()
    cache = paths.CACHE_DIR / "version_manifest_v2.json"
    if offline:
        return read_json(cache) or {"versions": []}
    if not force and cache.exists():
        age = time.time() - cache.stat().st_mtime
        cached = read_json(cache)
        if cached and age < MANIFEST_TTL_SECONDS:
            return cached
    try:
        manifest = fetch_json(VERSION_MANIFEST_URL)
    except Exception:
        cached = read_json(cache)
        if cached:
            return cached
        raise
    write_json(cache, manifest)
    return manifest


def manifest_versions(manifest: dict, show_all: bool = False) -> list[dict]:
    if show_all:
        versions = list(manifest.get("versions", []))
    else:
        versions = [v for v in manifest.get("versions", [])
                    if v.get("type") == "release"]
        versions = [v for v in versions if in_supported_range(v["id"])]
    return sorted(versions, key=lambda item: parse_version_key(item["id"]),
                  reverse=True)


def version_entry(manifest: dict, version_id: str) -> dict | None:
    for entry in manifest.get("versions", []):
        if entry.get("id") == version_id:
            return entry
    return None


def fetch_version_json(version_id: str, url: str) -> dict:
    """Descarga el <version>.json oficial y lo cachea en disco."""
    paths.ensure_dirs()
    cache = paths.CACHE_DIR / f"version-{version_id}.json"
    data = None
    if cache.exists():
        data = read_json(cache)
    if not data:
        data = fetch_json(url)
        write_json(cache, data)
    return data


def write_version_profile(version_id: str, payload: dict) -> Path:
    path = paths.version_json_path(version_id)
    write_json(path, payload)
    return path


# Instaladores Forge antiguos (1.12.x) escriben objetos rotos del tipo
# "{\n,\n\"url\": ...}" dentro de libraries: JSON invalido para json.loads.
_BROKEN_OBJECT = re.compile(r"\{\s*,[^{}]*\}")


# Cache en memoria de perfiles locales: el JSON solo cambia cuando el
# archivo se reescribe, asi que basta validar mtime+tamaño.
_PROFILE_CACHE: dict[Path, tuple[tuple[int, int], dict | None]] = {}


def _read_profile_json(path: Path) -> dict | None:
    try:
        stat = path.stat()
    except OSError:
        _PROFILE_CACHE.pop(path, None)
        return None
    stamp = (stat.st_mtime_ns, stat.st_size)
    cached = _PROFILE_CACHE.get(path)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    payload = _parse_profile_json(path)
    _PROFILE_CACHE[path] = (stamp, payload)
    return payload


def _parse_profile_json(path: Path) -> dict | None:
    payload = read_json(path)
    if payload is not None:
        return payload
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        return json.loads(_BROKEN_OBJECT.sub("{}", text))
    except ValueError:
        return None


def load_version_profile(version_id: str) -> dict | None:
    path = (paths.find_version_json(version_id)
            or paths.version_json_path(version_id))
    return _read_profile_json(path)


def local_profiles() -> list[str]:
    """Perfiles locales de todas las raices .minecraft conocidas."""
    profiles: list[str] = []
    seen: set[str] = set()
    for versions_dir in paths.versions_dirs():
        try:
            children = sorted(versions_dir.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir() or child.name in seen:
                continue
            if (child / f"{child.name}.json").exists():
                seen.add(child.name)
                profiles.append(child.name)
    return sorted(profiles)


def resolve_version(version_id: str) -> dict:
    """Carga una version y fusiona su cadena de herencia (OptiFine incluido)."""
    chain: list[dict] = []
    current = version_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        payload = load_version_profile(current)
        if payload is None:
            raise FileNotFoundError(
                f"Falta el perfil '{current}'. Descarga la version primero."
            )
        payload = dict(payload)
        payload.setdefault("id", current)
        chain.append(payload)
        current = payload.get("inheritsFrom")

    if not chain:
        raise FileNotFoundError(f"Perfil desconocido: {version_id}")

    base = chain[-1]
    merged = {
        "id": version_id,
        "base_id": base.get("id"),
        "type": chain[0].get("type") or base.get("type") or "release",
        "mainClass": None,
        "minecraftArguments": None,
        "arguments": {"game": [], "jvm": [], "default-user-jvm": []},
        "libraries": [],
        "assetIndex": None,
        "assets": None,
        "downloads": {},
        "javaVersion": None,
        "logging": {},
        "releaseTime": chain[0].get("releaseTime") or base.get("releaseTime"),
    }

    # Padre -> hijo, para que el perfil hijo pueda sobreescribir valores.
    for payload in reversed(chain):
        if payload.get("mainClass"):
            merged["mainClass"] = payload["mainClass"]
        if payload.get("minecraftArguments"):
            merged["minecraftArguments"] = payload["minecraftArguments"]
        arguments = payload.get("arguments") or {}
        merged["arguments"]["game"].extend(arguments.get("game") or [])
        merged["arguments"]["jvm"].extend(arguments.get("jvm") or [])
        merged["arguments"]["default-user-jvm"].extend(
            arguments.get("default-user-jvm") or [])
        merged["libraries"].extend(payload.get("libraries") or [])
        for key in ("assetIndex", "assets", "logging", "javaVersion", "type"):
            if payload.get(key):
                merged[key] = payload[key]
        downloads = payload.get("downloads") or {}
        if downloads:
            merged["downloads"].update(downloads)

    if merged["base_id"] is None:
        merged["base_id"] = version_id
    if not merged["mainClass"]:
        raise ValueError(f"El perfil '{version_id}' no define mainClass.")
    if not merged["assetIndex"]:
        raise ValueError(f"El perfil '{version_id}' no define assetIndex.")
    return merged


def required_java_major(version_json: dict) -> int:
    java = version_json.get("javaVersion") or {}
    major = java.get("majorVersion")
    if isinstance(major, int) and major > 0:
        return major
    return 8


def merge_local_and_manifest(manifest: dict, show_all: bool) -> list[dict]:
    """Lista de versiones: oficiales + perfiles locales (OptiFine)."""
    entries: list[dict] = []
    seen = set()
    for entry in manifest_versions(manifest, show_all=show_all):
        entries.append({"id": entry["id"],
                        "type": entry.get("type") or "release",
                        "local": False})
        seen.add(entry["id"])

    for profile_id in local_profiles():
        if profile_id in seen:
            continue
        payload = load_version_profile(profile_id) or {}
        parent = payload.get("inheritsFrom", "")
        if not show_all and parent and not in_supported_range(parent):
            continue
        entries.append({
            "id": profile_id,
            "type": "optifine" if "optifine" in profile_id.lower() else "local",
            "local": True,
        })
    return entries
