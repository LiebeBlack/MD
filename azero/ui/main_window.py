"""Ventana principal del launcher: barra lateral + paginas."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QPushButton,
                             QStackedWidget, QVBoxLayout, QWidget)

from .. import (APP_NAME, APP_VERSION, database, hardware, paths)
from ..auth import offline_uuid, validate_username
from ..constants import MEMORY_STEP_MB
from ..manifest import load_version_profile, local_profiles, parse_version_key
from ..optifine import inspect_installer
from ..settings import Settings
from ..workers import LaunchWorker, ManifestWorker, OptiFineWorker
from . import theme
from .pages import (AboutPage, AccountPage, PlayPage, SettingsPage,
                    VersionsPage)
from .widgets import Pill, faint_label


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _java_major_for(version_id: str) -> int:
    """Java recomendado si el perfil aun no esta descargado (heuristica)."""
    key = parse_version_key(version_id)
    if key >= (1, 20, 5):
        return 21
    if key >= (1, 17, 0):
        return 17
    return 8


def _version_entry_sort(entry: dict) -> tuple:
    """Ordena perfiles: version base descendente, luego Vanilla/Forge/
    OptiFine y parche descendente."""
    payload = load_version_profile(entry["id"]) or {}
    base = payload.get("inheritsFrom") or entry["id"]
    key = tuple(parse_version_key(base)) + (0,) * 3
    key = key[:3]
    lower = entry["id"].lower()
    kind = 2 if "optifine" in lower else 1 if "forge" in lower else 0
    patch = tuple(parse_version_key(entry["id"])) + (0,) * 3
    return (-key[0], -key[1], kind, -patch[2], entry["id"])


def _java_major_display(version_id: str) -> int:
    """Java real que usara el launcher, leido del perfil si existe."""
    payload = load_version_profile(version_id) or {}
    candidates = [payload]
    parent = payload.get("inheritsFrom")
    if parent:
        candidates.append(load_version_profile(parent) or {})
    for item in candidates:
        major = (item.get("javaVersion") or {}).get("majorVersion")
        if isinstance(major, int) and major > 0:
            return major
    return _java_major_for(version_id)


def _enable_dark_titlebar(window: QWidget) -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        value = ctypes.c_int(1)
        hwnd = int(window.winId())
        # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 2004+)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:  # noqa: BLE001 - es solo estetico
        pass


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self._entries: list[dict] = []
        self._manifest_worker: ManifestWorker | None = None
        self._launch_worker: LaunchWorker | None = None
        self._of_worker: OptiFineWorker | None = None
        self._session_id: int | None = None
        self._session_name = ""
        self._session_uuid = ""
        self._session_account = "offline"
        self._titlebar_done = False
        self._allow_close = False

        database.init_db()

        self.setWindowTitle(f"{APP_NAME} Launcher")
        self.resize(1120, 720)
        self.setMinimumSize(960, 640)
        if self.settings.win_geometry:
            try:
                self.restoreGeometry(
                    QByteArray.fromBase64(
                        self.settings.win_geometry.encode("ascii")))
            except Exception:  # noqa: BLE001 - geometria corrupta: ignorar
                pass

        self._build_ui()
        self._apply_settings()
        self._refresh_account()
        self._reload_versions()

        shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut.activated.connect(self._go_settings)
        play_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        play_shortcut.activated.connect(self._on_play_clicked)
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._reload_versions)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(lambda: self.console.clear())

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        columns = QHBoxLayout(root)
        columns.setContentsMargins(0, 0, 0, 0)
        columns.setSpacing(0)
        columns.addWidget(self._build_sidebar(), 0)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.play_page = PlayPage(self)
        self.versions_page = VersionsPage(self)
        self.account_page = AccountPage(self)
        self.settings_page = SettingsPage(self)
        self.about_page = AboutPage(self)
        self.stack.addWidget(self.play_page)
        self.stack.addWidget(self.versions_page)
        self.stack.addWidget(self.account_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.about_page)
        right_layout.addWidget(self.stack, 1)
        right_layout.addWidget(self._build_status_bar())

        # Atajos para compatibilidad con la logica de trabajadores.
        self.console = self.play_page.console
        self.progress = self.play_page.progress
        self.percent_label = self.play_page.percent_label
        self.stage_label = self.play_page.stage_label

        columns.addWidget(right, 1)
        self._go_page(0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(188)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 14, 10, 10)
        layout.setSpacing(3)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(9)
        icon = QLabel()
        icon.setPixmap(theme.app_icon().pixmap(30, 30))
        icon.setFixedSize(30, 30)
        brand_row.addWidget(icon)
        brand = QLabel(
            '<span style="color:#E8EEF7">AZero</span>'
            '<span style="color:#3DDC97">Craft</span>'
        )
        brand.setObjectName("brandTitle")
        brand.setTextFormat(Qt.TextFormat.RichText)
        brand.setStyleSheet("font-size: 14pt;")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(8)

        layout.addWidget(self._nav_label("MENU"))
        self.nav_buttons: list[QPushButton] = []
        for index, (icon_text, label) in enumerate((
                ("▶", "Jugar"),
                ("▦", "Versiones"),
                ("◉", "Cuenta"),
                ("⚙", "Ajustes"),
                ("i", "Acerca de"),
        )):
            button = QPushButton(f"  {icon_text}   {label}")
            button.setObjectName("navButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setCheckable(True)
            button.clicked.connect(
                lambda _=False, i=index: self._go_page(i))
            self.nav_buttons.append(button)
            layout.addWidget(button)

        layout.addStretch(1)

        layout.addWidget(self._nav_label("ESTADO"))
        self.side_status = Pill("LISTO", dim=True)
        self.side_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.side_status)
        layout.addSpacing(6)
        layout.addWidget(faint_label(f"{APP_NAME} {APP_VERSION} · portable"))
        return sidebar

    def _nav_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("navTitle")
        return label

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("statusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(10)
        self.status_label = QLabel("Listo para jugar.")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label, 1)
        self.ram_label = faint_label("")
        layout.addWidget(self.ram_label)
        layout.addWidget(faint_label("Ctrl+, ajustes · Ctrl+Enter jugar"))
        self._ram_timer = QTimer(self)
        self._ram_timer.setInterval(5000)
        self._ram_timer.timeout.connect(self._update_ram_label)
        self._ram_timer.start()
        self._update_ram_label()
        return bar

    def _update_ram_label(self) -> None:
        avail = hardware.ram_avail_mb()
        if avail:
            self.ram_label.setText(f"RAM libre: {avail / 1024:.1f} GB")

    # ------------------------------------------------------------ navegacion
    def _go_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, button in enumerate(self.nav_buttons):
            if button.property("active") != (i == index):
                button.setProperty("active", i == index)
                _repolish(button)
        if index == 1:
            self.versions_page.refresh_all()
        elif index == 2:
            self.account_page.refresh_accounts()
        elif index == 4:
            self.about_page.ensure_update_check()

    def _go_settings(self) -> None:
        if not self._is_busy():
            self._go_page(3)

    # -------------------------------------------------------------- estado
    def _launch_running(self) -> bool:
        return bool(self._launch_worker and self._launch_worker.isRunning())

    def _of_running(self) -> bool:
        return bool(self._of_worker and self._of_worker.isRunning())

    def _is_busy(self) -> bool:
        return self._launch_running() or self._of_running()

    def _selected_version(self) -> str:
        return self.play_page.version_combo.currentData() or ""

    def _selected_base(self) -> str:
        version_id = self._selected_version()
        if not version_id:
            return ""
        payload = load_version_profile(version_id) or {}
        return payload.get("inheritsFrom") or version_id

    def _active_identity(self) -> tuple[str, str, str, bool]:
        """(nombre, uuid, tipo_cuenta, online) de la cuenta activa."""
        key = (self.settings.active_account or "").strip()
        if key.startswith("ms:"):
            row = database.get_account(key[3:])
            if row:
                dashed = row["mc_uuid"]
                if len(dashed) == 32:
                    dashed = (f"{dashed[:8]}-{dashed[8:12]}-{dashed[12:16]}"
                              f"-{dashed[16:20]}-{dashed[20:]}")
                return row["mc_name"], dashed, "Microsoft", True
        name = self.settings.username.strip()
        error = validate_username(name)
        uuid_ = "" if error else offline_uuid(name)
        return name, uuid_, "Offline", False

    def _identity_valid(self) -> bool:
        name, _, _, online = self._active_identity()
        if online:
            return bool(name)
        return validate_username(name) is None

    def _refresh_state(self) -> None:
        busy = self._is_busy()
        has_version = self.play_page.version_combo.count() > 0
        page = self.play_page
        page.set_busy_widgets(busy)

        if self._launch_running():
            if self._session_id is not None:
                # El juego ya corre: el worker solo vigila el proceso, no
                # hay nada que cancelar desde el boton.
                page.play_button.setText("EN PARTIDA")
                page.play_button.setEnabled(False)
                self.side_status.setText("JUGANDO")
            else:
                page.play_button.setText("CANCELAR")
                page.play_button.setEnabled(True)
                self.side_status.setText("TRABAJANDO")
        elif self._of_running():
            page.play_button.setText("INSTALANDO…")
            page.play_button.setEnabled(False)
            self.side_status.setText("OPTIFINE")
        else:
            page.play_button.setText("JUGAR")
            page.play_button.setEnabled(
                self._identity_valid() and has_version)
            self.side_status.setText("LISTO")

        busy_property = busy
        if bool(page.play_button.property("busy")) != busy_property:
            page.play_button.setProperty("busy", busy_property)
            _repolish(page.play_button)

    def _set_status(self, text: str, kind: str = "normal") -> None:
        mapping = {"normal": "statusLabel", "error": "statusError",
                   "ok": "statusOk"}
        self.status_label.setText(text)
        self.status_label.setObjectName(mapping.get(kind, "statusLabel"))
        _repolish(self.status_label)

    def _set_progress(self, done: int, total: int) -> None:
        if total <= 0:
            self.progress.setRange(0, 0)
            self.percent_label.setText("")
            return
        self.progress.setRange(0, total)
        self.progress.setValue(min(done, total))
        self.percent_label.setText(f"{int(done * 100 / total)}%")

    def _refresh_account(self) -> None:
        key = self.settings.active_account or ""
        if key.startswith("ms:") and database.get_account(key[3:]) is None:
            self.settings.active_account = ""
            try:
                self.settings.save()
            except OSError:
                pass
        name, uuid_, kind, online = self._active_identity()
        if hasattr(self, "play_page"):
            self.play_page.refresh_account(name, uuid_, kind, online)
            edit = self.play_page.name_edit
            if edit.text().strip() != self.settings.username:
                edit.blockSignals(True)
                edit.setText(self.settings.username)
                edit.blockSignals(False)
        if hasattr(self, "account_page"):
            other = self.account_page.off_name
            if other.text().strip() != self.settings.username:
                other.blockSignals(True)
                other.setText(self.settings.username)
                other.blockSignals(False)
            error = validate_username(self.settings.username.strip())
            if error:
                self.account_page.off_uuid.setText("UUID pendiente")
                self.account_page.off_uuid.setToolTip(error)
                self.account_page.off_avatar.set_identity(
                    self.settings.username or "?", self.settings.username or "?")
            else:
                uuid_off = offline_uuid(self.settings.username.strip())
                self.account_page.off_uuid.setText(f"UUID {uuid_off}")
                self.account_page.off_uuid.setToolTip("UUID offline v3")
                self.account_page.off_avatar.set_identity(
                    self.settings.username.strip(), uuid_off)
            self.account_page.refresh_accounts()
        self._refresh_state()
        if not self._is_busy() and hasattr(self, "play_page") \
                and not self.play_page.version_combo.count():
            self._set_status("Cargando versiones…")

    def _apply_settings(self) -> None:
        page = self.play_page
        # valueChanged actualiza ram_value y settings.memory_mb.
        page.ram_slider.setValue(self.settings.memory_mb)
        page.auto_close_check.setChecked(self.settings.auto_close)
        page.server_edit.setText(self.settings.server)
        page.name_edit.setText(self.settings.username)

    def _save_settings(self) -> None:
        page = self.play_page
        self.settings.memory_mb = page.ram_slider.value()
        self.settings.auto_close = page.auto_close_check.isChecked()
        self.settings.server = page.server_edit.text().strip()
        self.settings.username = page.name_edit.text().strip()
        self.settings.version = self._selected_version() or self.settings.version
        try:
            self.settings.save()
        except OSError as error:
            self.console.append(f"No se pudieron guardar los ajustes: {error}")

    def _on_username_changed(self, text: str) -> None:
        self.settings.username = text.strip()
        if hasattr(self, "account_page"):
            other = self.account_page.off_name
            if other.text() != text:
                other.blockSignals(True)
                other.setText(text)
                other.blockSignals(False)
        self._refresh_account()

    # ------------------------------------------------------------ versiones
    def _reload_versions(self) -> None:
        if self._manifest_worker and self._manifest_worker.isRunning():
            return
        self.play_page.version_meta.setText(
            "Actualizando el manifiesto oficial…")
        worker = ManifestWorker(self.settings.show_all_versions, self)
        worker.ready.connect(self._on_manifest_ready)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(self._on_manifest_finished)
        self._manifest_worker = worker
        worker.start()

    def _on_manifest_ready(self, entries: list[dict]) -> None:
        self._entries = entries
        current = self.settings.version
        combo = self.play_page.version_combo
        combo.blockSignals(True)
        combo.clear()
        last_group = None
        for entry in sorted(entries, key=_version_entry_sort):
            payload = load_version_profile(entry["id"]) or {}
            base = payload.get("inheritsFrom") or entry["id"]
            bkey = tuple(parse_version_key(base)) + (0,) * 3
            group = f"{bkey[0]}.{bkey[1]}.x"
            if group != last_group:
                combo.addItem(f"── {group} ──")
                combo.model().item(combo.count() - 1).setEnabled(False)
                last_group = group
            label = entry["id"]
            if entry.get("local"):
                lower = label.lower()
                if "optifine" in lower:
                    label += "  · OptiFine"
                elif "forge" in lower:
                    label += "  · Forge"
                else:
                    label += "  · local"
            combo.addItem(label, entry["id"])
        index = combo.findData(current)
        if index < 0:
            # Preferir una version ya descargada (juego inmediato).
            installed = sorted(local_profiles(),
                               key=parse_version_key, reverse=True)
            index = -1
            for profile_id in installed:
                index = combo.findData(profile_id)
                if index >= 0:
                    break
            if index < 0:
                preferred = combo.findData("1.15.2")
                index = preferred if preferred >= 0 else 0
        if combo.count():
            combo.setCurrentIndex(index)
            self.settings.version = combo.currentData()
        combo.blockSignals(False)
        combo.setEnabled(True)
        self._update_version_meta()
        self._refresh_state()
        if not entries:
            self._set_status("No hay versiones disponibles sin conexión.", "error")
        else:
            self._set_status("Listo para jugar.", "ok")

    def _on_manifest_failed(self, message: str) -> None:
        self.console.append(message)
        profiles = [{"id": pid, "type": "local", "local": True}
                    for pid in local_profiles()]
        if profiles:
            self._on_manifest_ready(profiles)
            self._set_status("Sin manifiesto: solo perfiles locales.", "error")
        else:
            self._set_status("No se pudo cargar el manifiesto oficial.", "error")

    def _on_manifest_finished(self) -> None:
        worker = self._manifest_worker
        self._manifest_worker = None
        if worker:
            worker.deleteLater()
        self._refresh_state()

    def _on_version_changed(self) -> None:
        version_id = self._selected_version()
        if not version_id:
            return
        self.settings.version = version_id
        self._update_version_meta()
        if not self._is_busy():
            self._set_status("Listo para jugar.", "normal")

    def _update_version_meta(self) -> None:
        version_id = self._selected_version()
        if not version_id:
            self.play_page.version_meta.setText("Sin versiones cargadas.")
            return
        base = self._selected_base()
        payload = load_version_profile(version_id) or {}
        lower_id = version_id.lower()
        is_optifine = "optifine" in lower_id
        is_forge = "forge" in lower_id
        kind = ("OptiFine" if is_optifine
                else "Forge" if is_forge
                else ("Perfil local" if payload.get("inheritsFrom")
                      else "Vanilla"))
        if paths.version_jar_path(base).exists():
            state = "instalada"
        else:
            state = "se descargara al jugar"
        self.play_page.version_meta.setText(
            f"{base} · Java {_java_major_display(version_id)} · {kind} · {state}"
        )
        self._update_optifine_row(base)

    def _update_optifine_row(self, base: str) -> None:
        profiles = [pid for pid in local_profiles()
                    if base and pid.startswith(f"{base}-OptiFine_")]
        if profiles:
            edition = profiles[0].split("OptiFine_", 1)[-1].replace("_", " ")
            self.play_page.optifine_status.setText(f"Instalado · {edition}")
            self.play_page.optifine_button.setText("Reinstalar…")
        else:
            self.play_page.optifine_status.setText("No instalado · mas FPS y shaders")
            self.play_page.optifine_button.setText("Instalar…")

    # --------------------------------------------------------------- juego
    def play_version(self, version_id: str) -> None:
        """Lanza directamente una version instalada (desde Versiones)."""
        if self._is_busy():
            return
        combo = self.play_page.version_combo
        index = combo.findData(version_id)
        if index < 0:
            # Perfil local que el manifiesto no lista: se agrega para que
            # _selected_version() devuelva exactamente esta version.
            combo.addItem(f"{version_id}  · local", version_id)
            index = combo.count() - 1
        combo.setCurrentIndex(index)
        self.settings.version = version_id
        self._on_play_clicked()

    def delete_version(self, version_id: str) -> None:
        if self._is_busy():
            return
        target = paths.version_dir(version_id)
        if not target.exists():
            return
        answer = QMessageBox.question(
            self, "Eliminar version",
            f"Se eliminara '{version_id}' y todos sus archivos "
            "(cliente, perfil y nativos).\n\n"
            "Las librerias y assets compartidos se conservan.\n\n"
            "¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            shutil.rmtree(target)
        except OSError as error:
            QMessageBox.warning(self, "No se pudo eliminar",
                                str(error))
            return
        self.console.append(f"Version eliminada: {version_id}")
        self.versions_page.refresh_all()
        self._reload_versions()

    def _on_play_clicked(self) -> None:
        if self._launch_running():
            if self._launch_worker:
                self._launch_worker.cancel()
            self.play_page.play_button.setEnabled(False)
            self._set_status("Cancelando…")
            return
        if self._is_busy():
            return

        name, uuid_, account_kind, online = self._active_identity()
        if online:
            pass  # el nombre/uuid reales vienen de la cuenta Microsoft
        else:
            error = validate_username(name)
            if error:
                QMessageBox.warning(self, "Nombre inválido", error)
                return
        version_id = self._selected_version()
        if not version_id:
            QMessageBox.warning(self, "Sin versión",
                                "Selecciona una versión de Minecraft.")
            return

        self.settings.version = version_id
        self._save_settings()
        shown_name = name if online else self.settings.username.strip()
        self.console.append(f"=== {version_id} · {shown_name} ===")
        self._session_name = shown_name
        self._session_uuid = uuid_
        self._session_account = "microsoft" if online else "offline"
        self._set_progress(0, 0)
        self._set_status("Preparando el juego…")

        worker = LaunchWorker(version_id, self.settings, parent=self)
        worker.stage.connect(self._on_stage)
        worker.progress.connect(self._on_progress)
        worker.log.connect(self.console.append)
        worker.launched.connect(self._on_launched)
        worker.game_log.connect(self.console.append)
        worker.game_exit.connect(self._on_game_exit)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_launch_finished)
        self._launch_worker = worker
        worker.start()
        self._refresh_state()

    def _on_stage(self, text: str) -> None:
        self.stage_label.setText(text)
        self.console.append(f"• {text}")

    def _on_progress(self, done: int, total: int) -> None:
        self._set_progress(done, total)

    def _on_launched(self, pid: int, log_path: str, auto_close: bool) -> None:
        self._set_progress(1, 1)
        self._set_status(f"Minecraft iniciado (PID {pid}).", "ok")
        self.console.append(f"Minecraft iniciado · PID {pid}")
        self.console.append(f"Log del juego: {log_path}")
        self.stage_label.setText(
            "En ejecución · proceso independiente del launcher."
        )
        version_id = self._selected_version() or self.settings.version
        base = self._selected_base() or version_id
        jar_path = paths.version_jar_path(base)
        size = jar_path.stat().st_size if jar_path.exists() else 0
        database.log_download(
            "version", f"Cliente {version_id} listo",
            version_id=version_id, size_bytes=size, status="ok",
            detail=f"sesion como {self._session_name}")
        self._session_id = database.session_start(
            self._session_name, self._session_uuid, version_id,
            self._session_account, pid=pid)
        self._save_settings()
        self.versions_page.refresh_all()
        if auto_close:
            self.console.append("Autocierre activo: el launcher se cerrará ahora.")
            QTimer.singleShot(1200, self._quit_after_launch)
        self._refresh_state()

    def _quit_after_launch(self) -> None:
        self._allow_close = True
        self.close()
        QApplication.instance().quit()

    def _on_game_exit(self, code: int) -> None:
        self.console.append(f"Minecraft finalizó (código {code}).")
        if self._session_id is not None:
            database.session_end(self._session_id, exit_code=code)
            self._session_id = None
            self.versions_page.refresh_all()
        if not self._allow_close:
            self._set_status(f"Minecraft se cerró (código {code}).", "normal")

    def _on_failed(self, message: str) -> None:
        self.console.append(f"ERROR: {message}")
        database.log_download(
            "error", message.strip().splitlines()[0]
            if message.strip() else "Error desconocido",
            version_id=self._selected_version() or self.settings.version,
            status="error")
        if self._session_id is not None:
            database.session_end(self._session_id, detail="error")
            self._session_id = None
        first_line = (message.strip().splitlines()[0]
                      if message.strip() else "Error desconocido")
        self._set_status("No se pudo iniciar el juego.", "error")
        self._set_progress(0, 1)
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("No se pudo iniciar Minecraft")
        box.setText(first_line)
        box.setInformativeText(
            "Puedes revisar el registro completo y volver a intentarlo."
        )
        box.setDetailedText(message)
        box.exec()

    def _on_cancelled(self) -> None:
        self.console.append("Operación cancelada.")
        if self._session_id is not None:
            database.session_end(self._session_id, detail="cancelado")
            self._session_id = None
        self._set_progress(0, 1)
        self._set_status("Operación cancelada.", "normal")

    def _on_launch_finished(self) -> None:
        worker = self._launch_worker
        self._launch_worker = None
        if worker:
            worker.deleteLater()
        self._refresh_state()

    # ------------------------------------------------------------- optifine
    def _on_install_optifine(self) -> None:
        if self._is_busy():
            return
        base = self._selected_base()
        if not base:
            return
        selected, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar instalador de OptiFine", str(Path.home()),
            "Instalador de OptiFine (*.jar)",
        )
        if not selected:
            return
        installer = Path(selected)
        try:
            info = inspect_installer(installer)
        except Exception as error:  # noqa: BLE001 - se muestra al usuario
            QMessageBox.warning(self, "OptiFine no válido", str(error))
            return
        if info.mc_version != base:
            QMessageBox.warning(
                self, "Versión incompatible",
                f"El instalador es para Minecraft {info.mc_version} y tienes "
                f"{base} seleccionado.\n\nSelecciona {info.mc_version} en la lista "
                "y vuelve a intentarlo.",
            )
            return

        self.console.append(f"Preparando {info.display}…")
        self._set_status("Instalando OptiFine…")
        worker = OptiFineWorker(installer, base, self.settings, parent=self)
        worker.stage.connect(self._on_stage)
        worker.progress.connect(self._on_progress)
        worker.log.connect(self.console.append)
        worker.done.connect(self._on_optifine_done)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        worker.finished.connect(self._on_optifine_finished)
        self._of_worker = worker
        worker.start()
        self._refresh_state()

    def _on_optifine_done(self, profile_id: str) -> None:
        self.settings.optifine_profile = profile_id
        self.settings.version = profile_id
        self.settings.last_optifine = profile_id
        self._save_settings()
        self.console.append(f"Perfil disponible: {profile_id}")
        database.log_download("optifine", f"OptiFine {profile_id}",
                              version_id=profile_id, status="ok")
        self._set_status(f"{profile_id} listo.", "ok")
        self._reload_versions()

    def _on_optifine_finished(self) -> None:
        worker = self._of_worker
        self._of_worker = None
        if worker:
            worker.deleteLater()
        self._refresh_state()

    # ---------------------------------------------------------- ajustes UI
    def _on_ram_changed(self, value: int) -> None:
        rounded = int(round(value / MEMORY_STEP_MB) * MEMORY_STEP_MB)
        if rounded != value:
            self.play_page.ram_slider.setValue(rounded)
            return
        gb = f"{value / 1024:.1f}".rstrip("0").rstrip(".")
        self.play_page.ram_value.setText(f"{value} MB · {gb} GB")
        self.settings.memory_mb = value

    def _on_auto_close_changed(self, checked: bool) -> None:
        self.settings.auto_close = checked
        self._save_settings()

    def _on_server_changed(self) -> None:
        self.settings.server = self.play_page.server_edit.text().strip()
        self._save_settings()

    def _open_mc_folder(self) -> None:
        paths.ensure_dirs()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(paths.MC_DIR)))

    # --------------------------------------------------------------- window
    def showEvent(self, event) -> None:  # noqa: N802 - API de Qt
        super().showEvent(event)
        if not self._titlebar_done:
            self._titlebar_done = True
            _enable_dark_titlebar(self)

    def closeEvent(self, event) -> None:  # noqa: N802 - API de Qt
        try:
            self.settings.win_geometry = bytes(
                self.saveGeometry().toBase64()).decode("ascii")
        except Exception:  # noqa: BLE001
            pass
        self._save_settings()
        if self._launch_worker and self._launch_worker.isRunning():
            self._launch_worker.cancel()
            self._launch_worker.wait(1500)
        if self._of_worker and self._of_worker.isRunning():
            self._of_worker.cancel()
            self._of_worker.wait(1500)
        login_worker = getattr(
            getattr(self, "account_page", None), "_login_worker", None)
        if login_worker is not None and login_worker.isRunning():
            login_worker.cancel()
            login_worker.wait(1500)
        update_checker = getattr(
            getattr(self, "about_page", None), "_update_checker", None)
        if update_checker is not None and update_checker.isRunning():
            update_checker.wait(2000)
        forge_worker = getattr(
            getattr(self, "settings_page", None), "_forge_worker", None)
        if forge_worker is not None and forge_worker.isRunning():
            forge_worker.cancel()
            forge_worker.wait(1500)
        super().closeEvent(event)
