"""Utilidades de red, hashing y descargas concurrentes."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .constants import USER_AGENT

ProgressFn = Callable[[int, int], None]
LogFn = Callable[[str], None]
CancelFn = Callable[[], bool]


class DownloadError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


def open_url(url: str, timeout: float = 30.0) -> "urllib.request.addinfourl":
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
        },
    )
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_json(url: str, timeout: float = 30.0) -> dict:
    with open_url(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def human_size(num_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num_bytes) < 1024 or unit == "GB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} GB"


def sha1_of(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class DownloadTask:
    url: str
    dest: Path
    sha1: str | None = None
    sha256: str | None = None
    size: int | None = None
    label: str = ""


@dataclass
class _Progress:
    total: int = 0
    done: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)
    callback: ProgressFn | None = None
    last_emit: float = 0.0

    def add_total(self, amount: int) -> None:
        with self.lock:
            self.total += max(0, amount)

    def advance(self, amount: int, force: bool = False) -> None:
        with self.lock:
            self.done = max(0, self.done + amount)
            done, total = self.done, self.total
            now = time.monotonic()
            should_emit = force or (now - self.last_emit) >= 0.08
            if should_emit:
                self.last_emit = now
        if self.callback and should_emit:
            self.callback(done, total)


def task_satisfied(task: DownloadTask) -> bool:
    try:
        stat = task.dest.stat()
    except OSError:
        return False
    if task.size is not None and stat.st_size != task.size:
        return False
    if task.sha256:
        return sha256_of(task.dest).lower() == task.sha256.lower()
    # Verificar SHA1 de cada archivo existente seria costoso; se valida el
    # tamano para no re-descargar y la integridad se comprueba al descargar.
    if not task.sha1 and task.size is None and stat.st_size == 0:
        return False
    return True


def _download_one(task: DownloadTask, progress: _Progress, cancel: CancelFn | None,
                  retries: int = 3) -> None:
    if cancel and cancel():
        raise CancelledError("Descarga cancelada")
    if task_satisfied(task):
        progress.advance(task.size or 0)
        return

    task.dest.parent.mkdir(parents=True, exist_ok=True)
    part = task.dest.with_name(task.dest.name + ".part")
    last_error: Exception | None = None

    for attempt in range(retries):
        if cancel and cancel():
            raise CancelledError("Descarga cancelada")
        written = 0
        try:
            with open_url(task.url, timeout=30) as response, part.open("wb") as handle:
                while True:
                    if cancel and cancel():
                        raise CancelledError("Descarga cancelada")
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    written += len(chunk)
                    progress.advance(len(chunk))
            if task.sha1:
                actual = sha1_of(part)
                if actual.lower() != task.sha1.lower():
                    raise DownloadError(f"SHA1 invalido en {task.label or task.url}")
            if task.sha256:
                actual = sha256_of(part)
                if actual.lower() != task.sha256.lower():
                    raise DownloadError(f"SHA256 invalido en {task.label or task.url}")
            os.replace(part, task.dest)
            return
        except CancelledError:
            part.unlink(missing_ok=True)
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, OSError,
                DownloadError) as error:
            last_error = error
            progress.advance(-written)
            part.unlink(missing_ok=True)
            if attempt < retries - 1:
                time.sleep(0.8 * (attempt + 1))

    raise DownloadError(
        f"No se pudo descargar {task.label or task.url}: {last_error}"
    )


def download_many(tasks: Iterable[DownloadTask], on_progress: ProgressFn | None = None,
                  workers: int = 8, cancel: CancelFn | None = None,
                  log: LogFn | None = None) -> None:
    """Descarga una lista de tareas en paralelo y reporta bytes acumulados."""
    # Los manifiestos repiten librerias con distintos clasificadores pero el
    # mismo artefacto base; nunca dos hilos deben escribir el mismo archivo.
    unique: dict[str, DownloadTask] = {}
    for task in tasks:
        unique.setdefault(str(task.dest).lower(), task)
    tasks = list(unique.values())
    if not tasks:
        if on_progress:
            on_progress(0, 0)
        return

    progress = _Progress(callback=on_progress)
    for task in tasks:
        progress.add_total(task.size or 0)
    progress.callback and progress.callback(0, progress.total)

    if log:
        log(f"Descargando {len(tasks)} archivo(s) ({human_size(progress.total)})")

    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(_download_one, task, progress, cancel): task
                   for task in tasks}
        for future in as_completed(futures):
            try:
                future.result()
            except CancelledError:
                for pending in futures:
                    pending.cancel()
                raise
            except DownloadError as error:
                errors.append(str(error))
            except Exception as error:  # noqa: BLE001 - se reporta al usuario
                errors.append(f"{futures[future].label}: {error}")

    progress.advance(0, force=True)
    if errors:
        raise DownloadError("\n".join(errors[:4]))


def extract_zip(zip_path: Path, dest: Path, excludes: Iterable[str] = ()) -> int:
    """Extrae un zip sin permitir rutas fuera del destino."""
    dest.mkdir(parents=True, exist_ok=True)
    excluded = tuple(excludes)
    dest_resolved = dest.resolve()
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename
            if excluded and any(name.startswith(prefix) for prefix in excluded):
                continue
            target = (dest / name).resolve()
            try:
                target.relative_to(dest_resolved)
            except ValueError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as out:
                shutil.copyfileobj(source, out)
            count += 1
    return count
