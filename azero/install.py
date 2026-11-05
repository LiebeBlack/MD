"""Instalacion completa de una version: jar, librerias, nativos y assets."""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import assets, libraries, manifest, paths
from .util import (CancelledError, DownloadTask, download_many, human_size,
                   task_satisfied)


@dataclass
class TaskContext:
    """Callbacks de progreso compartidos entre el nucleo y la UI."""

    stage: Callable[[str], None] = lambda text: None
    progress: Callable[[int, int], None] = lambda done, total: None
    log: Callable[[str], None] = lambda text: None
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def check(self) -> None:
        if self.cancel_event.is_set():
            raise CancelledError("Operacion cancelada")


@dataclass
class PreparedGame:
    version_id: str
    base_id: str
    main_class: str
    classpath: list[Path]
    natives_dir: Path
    assets_dir: Path
    game_dir: Path
    version_json: dict
    java_major: int
    logging_path: Path | None


def ensure_profile(version_id: str, manifest_data: dict | None = None) -> dict:
    existing = manifest.load_version_profile(version_id)
    if existing:
        return existing
    manifest_data = manifest_data or manifest.fetch_manifest()
    entry = manifest.version_entry(manifest_data, version_id)
    if entry is None:
        raise FileNotFoundError(
            f"La version '{version_id}' no aparece en el manifiesto de Mojang."
        )
    payload = manifest.fetch_version_json(version_id, entry["url"])
    manifest.write_version_profile(version_id, payload)
    return payload


def _client_jar_task(version_json: dict) -> tuple[DownloadTask | None, Path]:
    base_id = version_json["base_id"]
    jar_path = paths.version_jar_path(base_id)
    client = (version_json.get("downloads") or {}).get("client")
    if not client:
        return None, jar_path
    return DownloadTask(
        url=client["url"],
        dest=jar_path,
        sha1=client.get("sha1"),
        size=client.get("size"),
        label=f"{base_id} client.jar",
    ), jar_path


def _logging_task(version_json: dict) -> tuple[DownloadTask | None, Path | None]:
    logging_cfg = (version_json.get("logging") or {}).get("client")
    if not logging_cfg:
        return None, None
    info = logging_cfg.get("file") or {}
    if not info.get("url"):
        return None, None
    dest = paths.ASSETS_DIR / "log_configs" / info.get("id", "client.xml")
    task = DownloadTask(
        url=info["url"],
        dest=dest,
        sha1=info.get("sha1"),
        size=info.get("size"),
        label=f"log config {info.get('id', '')}",
    )
    return task, dest


def prepare(version_id: str, ctx: TaskContext, with_assets: bool = True) -> PreparedGame:
    """Descarga y verifica todo lo necesario para lanzar la version."""
    ctx.check()
    ctx.stage("Leyendo manifiesto oficial")
    manifest_data = manifest.fetch_manifest()

    profile_payload = manifest.load_version_profile(version_id)
    if profile_payload is None:
        ctx.log(f"Descargando definicion de {version_id}...")
        profile_payload = ensure_profile(version_id, manifest_data)
    version_json = manifest.resolve_version(version_id)
    ctx.check()

    ctx.stage("Calculando archivos necesarios")
    tasks: list[DownloadTask] = []

    client_task, client_jar = _client_jar_task(version_json)
    if client_task:
        tasks.append(client_task)

    plan = libraries.build_library_plan(version_json)
    tasks.extend(plan.downloads)

    logging_task, logging_path = _logging_task(version_json)
    if logging_task:
        tasks.append(logging_task)

    asset_index = version_json["assetIndex"]
    index_payload = assets.ensure_asset_index(asset_index, log=ctx.log)
    ctx.log(f"Indice de assets {asset_index['id']}: "
            f"{len(index_payload.get('objects') or {})} objetos")

    if with_assets:
        asset_task_list, asset_total = assets.asset_tasks(index_payload)
        tasks.extend(asset_task_list)
    else:
        asset_total = 0

    pending = [task for task in tasks if not task_satisfied(task)]
    total_bytes = sum(task.size or 0 for task in pending)
    if pending:
        ctx.stage(f"Descargando Minecraft {version_json['base_id']} "
                  f"({human_size(total_bytes)})")
        download_many(pending, on_progress=ctx.progress, workers=12,
                      cancel=ctx.cancel_event.is_set, log=ctx.log)
    else:
        ctx.stage("Archivos del juego al dia")
        ctx.progress(1, 1)
        ctx.log("No hay descargas pendientes.")
    ctx.check()

    ctx.stage("Extrayendo librerias nativas")
    natives_target = paths.natives_dir(version_id)
    if natives_target.exists():
        shutil.rmtree(natives_target, ignore_errors=True)
    libraries.extract_natives(plan, natives_target, log=ctx.log)
    ctx.check()

    if asset_total == 0 and with_assets:
        ctx.log("Assets al dia")

    classpath: list[Path] = []
    seen: set[str] = set()
    missing: list[Path] = []
    for entry in [*plan.classpath, client_jar]:
        key = str(entry).lower()
        if key in seen:
            continue
        seen.add(key)
        if entry.exists():
            classpath.append(entry)
        else:
            missing.append(entry)

    if missing:
        names = ", ".join(path.name for path in missing[:3])
        raise FileNotFoundError(
            f"Faltan librerias para {version_id}: {names}. "
            "Si usas OptiFine, vuelve a instalarlo."
        )

    return PreparedGame(
        version_id=version_id,
        base_id=version_json["base_id"],
        main_class=version_json["mainClass"],
        classpath=classpath,
        natives_dir=natives_target,
        assets_dir=paths.ASSETS_DIR,
        game_dir=paths.MC_DIR,
        version_json=version_json,
        java_major=manifest.required_java_major(version_json),
        logging_path=logging_path,
    )
