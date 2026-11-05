"""Hilos de trabajo (QThread) que mantienen la UI fluida."""

from __future__ import annotations

import threading
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from . import launch, manifest, msauth, optifine
from .install import TaskContext
from .util import CancelledError


class ManifestWorker(QThread):
    ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, show_all: bool, parent=None):
        super().__init__(parent)
        self.show_all = show_all

    def run(self) -> None:
        try:
            data = manifest.fetch_manifest()
            entries = manifest.merge_local_and_manifest(data, self.show_all)
            self.ready.emit(entries)
        except Exception as error:  # noqa: BLE001 - se informa en la UI
            self.failed.emit(f"No se pudo leer el manifiesto: {error}")


class LaunchWorker(QThread):
    stage = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    launched = pyqtSignal(int, str, bool)
    game_log = pyqtSignal(str)
    game_exit = pyqtSignal(int)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, version_id: str, settings, with_assets: bool = True,
                 parent=None):
        super().__init__(parent)
        self.version_id = version_id
        self.settings = settings
        self.with_assets = with_assets
        self._cancel = threading.Event()
        self._handle: launch.LaunchHandle | None = None

    def cancel(self) -> None:
        self._cancel.set()

    def _context(self) -> TaskContext:
        return TaskContext(
            stage=self.stage.emit,
            progress=self.progress.emit,
            log=self.log.emit,
            cancel_event=self._cancel,
        )

    def run(self) -> None:
        try:
            outcome = launch.install_and_launch(
                self.version_id, self.settings, self._context(),
                with_assets=self.with_assets,
                on_spawned=self._on_spawned,
            )
        except CancelledError:
            self.cancelled.emit()
            return
        except Exception as error:  # noqa: BLE001 - se muestra el mensaje real
            self.failed.emit(str(error))
            return

        self.launched.emit(outcome.pid, str(outcome.log_path), outcome.auto_close)
        if not outcome.auto_close and self._handle is not None:
            self._stream_game_log(self._handle)

    def _on_spawned(self, handle: launch.LaunchHandle) -> None:
        self._handle = handle

    def _stream_game_log(self, handle: launch.LaunchHandle) -> None:
        offset = 0

        def drain() -> None:
            nonlocal offset
            try:
                with handle.log_path.open("rb") as stream:
                    stream.seek(offset)
                    chunk = stream.read()
                    offset = stream.tell()
            except OSError:
                return
            for line in chunk.decode("utf-8", errors="replace").splitlines():
                if line.strip():
                    self.game_log.emit(line)

        while handle.process.poll() is None:
            time.sleep(0.4)
            drain()
        drain()  # leer el tramo final que quedo en el buffer del archivo
        try:
            handle.log_handle.close()
        except (OSError, ValueError):
            pass
        self.game_exit.emit(handle.process.returncode or 0)


class OptiFineWorker(QThread):
    stage = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    log = pyqtSignal(str)
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, installer: Path, base_version: str, settings, parent=None):
        super().__init__(parent)
        self.installer = installer
        self.base_version = base_version
        self.settings = settings
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def _context(self) -> TaskContext:
        return TaskContext(
            stage=self.stage.emit,
            progress=self.progress.emit,
            log=self.log.emit,
            cancel_event=self._cancel,
        )

    def run(self) -> None:
        try:
            info = optifine.install_optifine(
                self.installer, self.base_version, self.settings, self._context()
            )
        except CancelledError:
            self.log.emit("Instalacion de OptiFine cancelada.")
            return
        except Exception as error:  # noqa: BLE001
            self.failed.emit(str(error))
            return
        self.done.emit(info.profile_id)


class MSLoginWorker(QThread):
    """Inicio de sesion Microsoft por codigo de dispositivo."""

    code_ready = pyqtSignal(object)   # msauth.DeviceCode
    done = pyqtSignal(object, str)    # msauth.McSession, refresh_token
    failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = threading.Event()

    def cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            session, refresh = msauth.login_with_device_code(
                on_code=self.code_ready.emit,
                cancel=self._cancel.is_set,
            )
        except msauth.MsaCancelled:
            return
        except Exception as error:  # noqa: BLE001 - se muestra al usuario
            self.failed.emit(str(error))
            return
        self.done.emit(session, refresh)
