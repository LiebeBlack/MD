"""Indice de assets y descarga de objetos por hash."""

from __future__ import annotations

import hashlib
from typing import Callable

from . import paths
from .constants import RESOURCES_URL
from .util import DownloadTask, fetch_json, read_json, write_json

IndexProgress = Callable[[str], None]


def _sha1_file(path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def corrupt_objects(index: dict) -> list:
    """Rutas de objetos de assets cuyo sha1 no coincide con el indice.

    El nombre del archivo ES el hash, asi que basta recalcularlo; un
    objeto corrupto con tamano correcto pasaba desapercibido y el juego
    mostraba texturas rotas para siempre.
    """
    bad = []
    objects_dir = paths.ASSETS_DIR / "objects"
    for entry in (index.get("objects") or {}).values():
        digest = entry.get("hash")
        if not digest:
            continue
        target = objects_dir / digest[:2] / digest
        if not target.is_file():
            continue  # los ausentes los gestiona la descarga normal
        try:
            if _sha1_file(target).lower() != str(digest).lower():
                bad.append(target)
        except OSError:
            bad.append(target)
    return bad


def ensure_asset_index(index_meta: dict, log=None,
                       offline: bool = False) -> dict:
    index_id = index_meta["id"]
    target = paths.ASSETS_DIR / "indexes" / f"{index_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        cached = read_json(target)
        if cached:
            return cached

    if offline:
        # Sin conexion no se puede bajar el indice: se continua sin
        # verificacion de assets (el juego arranca igual).
        if log:
            log(f"Indice de assets {index_id} no esta en cache; "
                "se omitiran los assets en este lanzamiento.")
        return {}

    if log:
        log(f"Descargando indice de assets {index_id}")
    payload = fetch_json(index_meta["url"])
    write_json(target, payload)
    return payload


def asset_tasks(index: dict) -> tuple[list[DownloadTask], int]:
    tasks: list[DownloadTask] = []
    total = 0
    objects_dir = paths.ASSETS_DIR / "objects"
    for name, entry in (index.get("objects") or {}).items():
        digest = entry.get("hash")
        if not digest:
            continue
        size = int(entry.get("size") or 0)
        dest = objects_dir / digest[:2] / digest
        tasks.append(DownloadTask(
            url=f"{RESOURCES_URL}/{digest[:2]}/{digest}",
            dest=dest,
            sha1=digest,
            size=size,
            label=name,
        ))
        total += size
    return tasks, total
