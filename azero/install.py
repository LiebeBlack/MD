"""Instalacion completa de una version: jar, librerias, nativos y assets."""

from __future__ import annotations

import shutil
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import assets, libraries, manifest, paths
from .util import (CancelledError, DownloadTask, download_many, human_size,
                   read_json, task_satisfied)


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


def ensure_profile_chain(version_id: str,
                         manifest_data: dict | None = None,
                         offline: bool = False) -> None:
    """Garantiza el json de la version y de toda su cadena inheritsFrom.

    Los perfiles Forge/OptiFine heredan de la version vanilla; si el json
    padre falta (nunca se descargo o quedo a medias), resolve_version
    fallaba aunque el perfil hijo existiera. Los padres siempre son
    versiones oficiales localizables en el manifiesto de Mojang.
    """
    if manifest_data is None:
        manifest_data = manifest.fetch_manifest(offline=offline)
    current = version_id
    seen: set[str] = set()
    while current and current not in seen:
        seen.add(current)
        payload = manifest.load_version_profile(current)
        if payload is None:
            entry = manifest.version_entry(manifest_data, current)
            if entry is None and offline:
                # Sin manifiesto se puede recuperar el json desde la
                # cache del launcher si ya se descargo antes.
                cached = read_json(
                    paths.CACHE_DIR / f"version-{current}.json")
                if cached:
                    manifest.write_version_profile(current, cached)
                    payload = cached
            if payload is None:
                if entry is None:
                    raise FileNotFoundError(
                        f"El perfil '{current}' no existe localmente ni en "
                        "el manifiesto de Mojang.")
                payload = manifest.fetch_version_json(current, entry["url"])
                manifest.write_version_profile(current, payload)
        current = payload.get("inheritsFrom")


def _client_jar_task(version_json: dict) -> tuple[DownloadTask | None, Path]:
    base_id = version_json["base_id"]
    # Si el jar ya existe en otra raiz .minecraft registrada se reutiliza;
    # si no, se descarga en la raiz oficial.
    jar_path = (paths.find_version_jar(base_id)
                or paths.version_jar_path(base_id))
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


def prepare(version_id: str, ctx: TaskContext, with_assets: bool = True,
            offline: bool = False) -> PreparedGame:
    """Descarga y verifica todo lo necesario para lanzar la version.

    Con ``offline=True`` no se exigen manifiesto, indices ni hashes:
    se usan los archivos locales tal cual y las descargas que fallen se
    toleran (el chequeo final de classpath sigue siendo estricto).
    """
    ctx.check()
    ctx.stage("Leyendo manifiesto oficial")
    try:
        manifest_data = manifest.fetch_manifest(offline=offline)
    except Exception as error:  # noqa: BLE001 - se intenta con perfiles
        ctx.log(f"Manifiesto no disponible ({error}); "
                "se usaran los perfiles locales.")
        manifest_data = {}

    if manifest.load_version_profile(version_id) is None:
        ctx.log(f"Descargando definicion de {version_id}...")
    ensure_profile_chain(version_id, manifest_data, offline=offline)
    version_json = manifest.resolve_version(version_id)
    if libraries.fix_authlib_session(version_json, offline=offline):
        ctx.log("Authlib 2.1.28 -> 2.3.31 "
                "(multijugador corregido para 1.16.4/1.16.5)")
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
    index_payload = assets.ensure_asset_index(
        asset_index, log=ctx.log, offline=offline)
    ctx.log(f"Indice de assets {asset_index['id']}: "
            f"{len(index_payload.get('objects') or {})} objetos")

    if with_assets:
        asset_task_list, asset_total = assets.asset_tasks(index_payload)
        tasks.extend(asset_task_list)
    else:
        asset_total = 0

    if offline:
        # Sin verificacion de hashes: los archivos locales se aceptan por
        # tamano y una descarga corrupta no debe impedir el lanzamiento.
        for task in tasks:
            task.sha1 = None
            task.sha256 = None

    pending = [task for task in tasks if not task_satisfied(task)]
    total_bytes = sum(task.size or 0 for task in pending)
    if offline and pending:
        # Sin internet no se intenta descargar nada: cada intento
        # tardaria decenas de segundos en timeouts. Se continua solo
        # con lo que ya esta en el .minecraft local; el chequeo final
        # de classpath sigue siendo estricto para no lanzar a ciegas.
        ctx.log(f"{len(pending)} archivo(s) no estan en la cache local; "
                "se omitiran en este lanzamiento.")
        ctx.progress(1, 1)
    elif pending:
        ctx.stage(f"Descargando Minecraft {version_json['base_id']} "
                  f"({human_size(total_bytes)})")
        try:
            download_many(pending, on_progress=ctx.progress, workers=12,
                          cancel=ctx.cancel_event.is_set, log=ctx.log)
        except CancelledError:
            raise
        ctx.check()
    else:
        ctx.stage("Archivos del juego al dia")
        ctx.progress(1, 1)
        ctx.log("No hay descargas pendientes.")
    ctx.check()

    if not offline:
        # Verificacion SHA-1 pre-lanzamiento: detecta jars y objetos de
        # assets corruptos y los repara re-descargandolos.
        ctx.stage("Verificando integridad de archivos")
        client_sha1 = ((version_json.get("downloads") or {})
                       .get("client") or {}).get("sha1")
        extra = ([(client_jar, client_sha1)] if client_sha1 else [])
        corrupt = libraries.verify_checksums(version_json, extra=extra)
        if with_assets:
            corrupt += assets.corrupt_objects(index_payload)
        if corrupt:
            ctx.log(f"{len(corrupt)} archivo(s) corrupto(s); reparando…")
            for target in corrupt:
                target.unlink(missing_ok=True)
            repair = [task for task in tasks if not task_satisfied(task)]
            if repair:
                download_many(repair, on_progress=ctx.progress, workers=8,
                              cancel=ctx.cancel_event.is_set, log=ctx.log)
            ctx.check()
            remaining = libraries.verify_checksums(version_json,
                                                   extra=extra)
            if with_assets:
                remaining += assets.corrupt_objects(index_payload)
            if remaining:
                raise RuntimeError(
                    f"No se pudieron reparar {len(remaining)} archivo(s). "
                    "Revisa tu conexion e intentalo de nuevo.")
            ctx.log("Archivos reparados correctamente.")
        ctx.check()

    ctx.stage("Extrayendo librerias nativas")
    natives_target = paths.natives_dir(version_id)
    if natives_target.exists():
        shutil.rmtree(natives_target, ignore_errors=True)
    libraries.extract_natives(plan, natives_target, log=ctx.log)
    ctx.check()

    if asset_total == 0 and with_assets:
        ctx.log("Assets al dia" if index_payload.get("objects")
                else "Sin indice de assets: se omitio la verificacion.")

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
        java_major=manifest.preferred_java_major(
            version_id, version_json.get("base_id") or ""),
        logging_path=logging_path,
    )
