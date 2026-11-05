"""Indice de assets y descarga de objetos por hash."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from . import paths
from .constants import RESOURCES_URL
from .util import DownloadTask, fetch_json, read_json, write_json

IndexProgress = Callable[[str], None]


def ensure_asset_index(index_meta: dict, log=None) -> dict:
    index_id = index_meta["id"]
    target = paths.ASSETS_DIR / "indexes" / f"{index_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        cached = read_json(target)
        if cached:
            return cached

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
