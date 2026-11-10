"""Ventana principal del launcher: barra superior, pestañas y páginas."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PyQt6.QtCore import QByteArray, QSize, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel,
                             QMainWindow, QMessageBox, QSizePolicy,
                             QStackedWidget, QTabBar, QVBoxLayout, QWidget)

from .. import APP_NAME, APP_VERSION, database, mods, paths
from ..auth import offline_uuid, validate_username
from ..constants import MEMORY_STEP_MB
from ..loaders import loader_kind, mod_loader_kind
from .. import manifest
from ..manifest import load_version_profile, local_profiles, parse_version_key
from ..optifine import inspect_installer
from ..settings import Settings
from ..workers import LaunchWorker, ManifestWorker, OptiFineWorker
from . import theme
from .pages import (AboutPage, AccountPage, PlayPage, SettingsPage,
                    VersionsPage)
from .widgets import faint_label, make_button, repolish


def _center_window(window: QWidget) -> None:
    """Centra la ventana en la pantalla disponible (primer arranque)."""
    screen = window.screen() or QApplication.primaryScreen()
    if screen is None:
        return
    frame = window.frameGeometry()
    frame.moveCenter(screen.availableGeometry().center())
    window.move(frame.topLeft())


def _java_major_display(version_id: str,
                        payload: dict | None = None) -> int:
    """Versión de Java que usará el launcher, leída del perfil si existe."""
    if payload is None:
        payload = load_version_profile(version_id) or {}
    base = payload.get("inheritsFrom") or version_id
    preferred = manifest.preferred_java_major(version_id, base)
    if preferred > 8:
        return preferred
    # Version no parseable (p. ej. id de loader sin base): fiarse del
    # javaVersion declarado por el perfil.
    candidates = [payload]
    parent = payload.get("inheritsFrom")
    if parent:
        candidates.append(load_version_profile(parent) or {})
    for item in candidates:
        major = (item.get("javaVersion") or {}).get("majorVersion")
        if isinstance(major, int) and major > 0:
            return major
    return preferred


def _apply_titlebar_theme(window: QWidget, dark: bool) -> None:
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes

        value = ctypes.c_int(1 if dark else 0)
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
        self._launch_notices_shown: set[str] = set()
        self._page_specs = (
            ("Jugar", "play"),
            ("Versiones", "versions"),
            ("Cuenta", "account"),
            ("Ajustes", "settings"),
            ("Acerca de", "about"),
        )

        database.init_db()
        paths.set_extra_mc_dirs(
            line.strip()
            for line in settings.extra_mc_dirs.splitlines()
            if line.strip())

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
        else:
            _center_window(self)

        self._build_ui()
        self._apply_settings()
        self._refresh_account()
        self._reload_versions()
        # Si la sesion anterior cerro con mods en cuarentena (p. ej. por
        # autocierre), se devuelven a mods/ ahora que la UI esta lista.
        self._restore_quarantined_mods()

        shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut.activated.connect(self._go_settings)
        play_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        play_shortcut.activated.connect(self._on_play_clicked)
        version_shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        version_shortcut.activated.connect(self._focus_version_picker)
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._reload_versions)
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(lambda: self.console.clear())
        for index in range(5):
            nav_shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            nav_shortcut.activated.connect(
                lambda idx=index: self._go_page(idx))
        next_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        next_shortcut.activated.connect(lambda: self._cycle_tabs(1))
        prev_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        prev_shortcut.activated.connect(lambda: self._cycle_tabs(-1))
        page_down = QShortcut(QKeySequence("Ctrl+PageDown"), self)
        page_down.activated.connect(lambda: self._cycle_tabs(1))
        page_up = QShortcut(QKeySequence("Ctrl+PageUp"), self)
        page_up.activated.connect(lambda: self._cycle_tabs(-1))

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

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

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_app_bar())
        layout.addWidget(self.stack, 1)
        layout.addWidget(self._build_status_bar())

        # Atajos para compatibilidad con la logica de trabajadores.
        self.console = self.play_page.console
        self.progress = self.play_page.progress
        self.percent_label = self.play_page.percent_label
        self.stage_label = self.play_page.stage_label

        self._go_page(0)

    def _build_app_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("appBar")
        bar.setFixedHeight(50)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(12)

        icon = QLabel()
        icon.setPixmap(theme.app_icon().pixmap(28, 28))
        icon.setFixedSize(28, 28)
        layout.addWidget(icon)

        self.brand_title = QLabel()
        self.brand_title.setObjectName("brandTitle")
        self.brand_title.setTextFormat(Qt.TextFormat.RichText)
        self._refresh_brand()
        layout.addWidget(self.brand_title)
        layout.addSpacing(8)

        self.tabs = QTabBar()
        self.tabs.setObjectName("browserTabs")
        self.tabs.setExpanding(False)
        self.tabs.setMovable(False)
        self.tabs.setTabsClosable(False)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.tabs.setUsesScrollButtons(False)
        self.tabs.setDrawBase(False)
        self.tabs.setIconSize(QSize(16, 16))
        self.tabs.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.tabs.setSizePolicy(QSizePolicy.Policy.Fixed,
                                QSizePolicy.Policy.Fixed)
        self.tabs.setAccessibleName("Navegación")
        self.tabs.setToolTip(
            "Navegación · Ctrl+Tab · Ctrl+1–5")
        for index in range(len(self._page_specs)):
            self._add_page_tab(index)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch(1)

        self.theme_button = make_button(
            "", "icon", "Cambiar entre tema claro y oscuro",
            self._toggle_theme)
        self.theme_button.setFixedSize(32, 32)
        self._refresh_theme_button()
        layout.addWidget(self.theme_button, 0, Qt.AlignmentFlag.AlignVCenter)
        return bar

    def _add_page_tab(self, page_index: int) -> int:
        label, kind = self._page_specs[page_index]
        index = self.tabs.addTab(
            theme.nav_icon(kind, theme.COLORS["TEXT_DIM"]), label)
        self.tabs.setTabData(index, page_index)
        self.tabs.setTabToolTip(
            index, f"{label} · Ctrl+{page_index + 1}")
        return index

    def _tab_index_for_page(self, page_index: int) -> int:
        for index in range(self.tabs.count()):
            if self.tabs.tabData(index) == page_index:
                return index
        return -1

    def _refresh_tab_icons(self) -> None:
        current = self.tabs.currentIndex()
        for index in range(self.tabs.count()):
            page = self.tabs.tabData(index)
            if page is None:
                continue
            _, kind = self._page_specs[page]
            color = (theme.COLORS["ACCENT"] if index == current
                     else theme.COLORS["TEXT_DIM"])
            self.tabs.setTabIcon(index, theme.nav_icon(kind, color))

    def _on_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        page = self.tabs.tabData(index)
        if page is None:
            return
        self.stack.setCurrentIndex(page)
        self._refresh_page(page)
        self._refresh_tab_icons()

    def _cycle_tabs(self, delta: int) -> None:
        count = self.tabs.count()
        if count < 2:
            return
        self.tabs.setCurrentIndex(
            (self.tabs.currentIndex() + delta) % count)

    def _refresh_brand(self) -> None:
        text = theme.COLORS["TEXT"]
        accent = theme.COLORS["ACCENT"]
        self.brand_title.setText(
            f'<span style="color:{text}">AZero</span>'
            f'<span style="color:{accent}">Craft</span>'
        )

    def _refresh_theme_button(self) -> None:
        dark = theme.current_theme_name() == "dark"
        self.theme_button.setText("☀" if dark else "☾")
        self.theme_button.setToolTip(
            "Cambiar al tema claro" if dark else "Cambiar al tema oscuro")
        self.theme_button.setAccessibleName(
            "Cambiar al tema claro" if dark else "Cambiar al tema oscuro")

    def _toggle_theme(self) -> None:
        name = ("light" if theme.current_theme_name() == "dark"
                else "dark")
        self._apply_ui_theme(name)

    def _apply_ui_theme(self, name: str) -> None:
        """Cambia el tema de toda la interfaz y guarda la preferencia."""
        name = name if name in theme.THEMES else "light"
        self.settings.ui_theme = name
        try:
            self.settings.save()
        except OSError:
            pass
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, name)
        _apply_titlebar_theme(self, name == "dark")
        self._refresh_brand()
        self._refresh_theme_button()
        # Las vistas que fijan QColor en tiempo de construccion (arbol de
        # versiones, fechas) deben reconstruirse con la nueva paleta.
        picker = getattr(getattr(self, "play_page", None),
                         "version_picker", None)
        if picker is not None:
            picker.invalidate()
        if hasattr(self, "versions_page"):
            self.versions_page.refresh_all()
        settings_page = getattr(self, "settings_page", None)
        if settings_page is not None:
            settings_page.refresh_theme_segment()
        if hasattr(self, "tabs"):
            repolish(self.tabs)
            self._refresh_tab_icons()
        self._refresh_state()

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("statusBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setProperty("kind", "normal")
        self.status_dot.setFixedSize(8, 8)
        layout.addWidget(self.status_dot)
        self.status_label = QLabel("Listo.")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label, 1)
        self.version_label = faint_label(f"v{APP_VERSION}")
        self.version_label.setWordWrap(False)
        layout.addWidget(self.version_label)
        return bar

    # ------------------------------------------------------------ navegacion
    def _refresh_page(self, index: int) -> None:
        if index == 0:
            self._refresh_state()
        elif index == 1:
            self.versions_page.refresh_all()
        elif index == 2:
            self.account_page.refresh_accounts()
        elif index == 4:
            self.about_page.ensure_update_check()

    def _go_page(self, index: int) -> None:
        """Abre o enfoca una pestaña de la aplicación."""
        if not 0 <= index < len(self._page_specs):
            return
        tab_index = self._tab_index_for_page(index)
        if tab_index < 0:
            return
        if self.tabs.currentIndex() != tab_index:
            self.tabs.blockSignals(True)
            self.tabs.setCurrentIndex(tab_index)
            self.tabs.blockSignals(False)
        self.stack.setCurrentIndex(index)
        self._refresh_page(index)
        self._refresh_tab_icons()

    def _go_settings(self) -> None:
        if not self._is_busy():
            self._go_page(3)

    def _focus_version_picker(self) -> None:
        """Abre el selector de versiones con el teclado (Ctrl+K)."""
        if self._is_busy():
            return
        self._go_page(0)
        picker = self.play_page.version_picker
        picker.setFocus(Qt.FocusReason.ShortcutFocusReason)
        picker.click()

    # -------------------------------------------------------------- estado
    def _launch_running(self) -> bool:
        return bool(self._launch_worker and self._launch_worker.isRunning())

    def _of_running(self) -> bool:
        return bool(self._of_worker and self._of_worker.isRunning())

    def _is_busy(self) -> bool:
        return self._launch_running() or self._of_running()

    def _selected_version(self) -> str:
        # Durante la construccion de PlayPage el atributo aun no existe;
        # los widgets que consultan la version seleccionada deben recibir "".
        page = getattr(self, "play_page", None)
        if page is None:
            return ""
        return page.version_picker.current_id() or ""

    def _selected_base(self) -> str:
        version_id = self._selected_version()
        if not version_id:
            return ""
        payload = load_version_profile(version_id) or {}
        return payload.get("inheritsFrom") or version_id

    def _mods_launch_issues(self, version_id: str) -> list[tuple]:
        """Devuelve cada mod que no se cargaría en esta versión y el motivo.

        Solo se aplica a perfiles con loader: en Vanilla y OptiFine,
        el juego ignora la carpeta mods/ y no hay nada que desactivar."""
        kind = mod_loader_kind(version_id)
        if not kind:
            return []
        installed = mods.list_mods()
        if not installed:
            return []
        issues = [
            (mod, f"requiere {mod.loader}; este perfil usa {kind}")
            for mod in mods.incompatible_loader_mods(installed, kind)]
        base = self._selected_base() or version_id
        issues.extend(
            (mod, f"declara MC {dep}; incompatible con {base}")
            for mod, dep in mods.incompatible_mods(installed, base))
        return issues

    def _quarantine_incompatible_mods(self, version_id: str) -> bool:
        """Aparta los mods incompatibles durante esta sesión de juego.

        Devuelve False si no se pudo mover algún mod. En ese caso, se
        cancela el inicio para evitar posibles errores en el juego."""
        issues = self._mods_launch_issues(version_id)
        if not issues:
            return True
        moved = mods.quarantine_mods([mod.path for mod, _ in issues])
        moved_names = {path.name for path in moved}
        active = [(mod, reason) for mod, reason in issues
                  if mod.name in moved_names]
        failed = [(mod, _reason) for mod, _reason in issues
                  if mod.name not in moved_names]
        if failed:
            # Los que si se movieron vuelven a mods/: no se lanza nada.
            mods.restore_quarantined()
            names = ", ".join(mod.title or mod.name for mod, _ in failed[:3])
            extra = f" +{len(failed) - 3}" if len(failed) > 3 else ""
            QMessageBox.warning(
                self, "Mods incompatibles",
                f"No se pudieron desactivar temporalmente: "
                f"{names}{extra}.\n\nEl juego podría fallar al iniciar; "
                "revisa la carpeta mods/ en Ajustes > Mods.")
            return False
        if active:
            self.console.append(
                "Mods desactivados para esta sesión: " + "; ".join(
                    f"{mod.title or mod.name} ({reason})"
                    for mod, reason in active))
            self.play_page._refresh_mods_status()
        return True

    def _restore_quarantined_mods(self) -> None:
        """Devuelve a mods/ los archivos JAR apartados en la sesión anterior."""
        restored = mods.restore_quarantined()
        if restored:
            self.console.append(
                f"{restored} mod(s) reactivados en la carpeta mods/.")
            self.play_page._refresh_mods_status()

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
        has_version = self.play_page.version_picker.count() > 0
        page = self.play_page
        page.set_busy_widgets(busy)

        if self._launch_running():
            if self._session_id is not None:
                # El juego ya corre: el worker solo vigila el proceso, no
                # hay nada que cancelar desde el boton.
                page.play_button.setText("EN PARTIDA")
                page.play_button.setEnabled(False)
            else:
                page.play_button.setText("CANCELAR")
                page.play_button.setEnabled(True)
        elif self._of_running():
            page.play_button.setText("INSTALANDO…")
            page.play_button.setEnabled(False)
        else:
            page.play_button.setText("JUGAR")
            page.play_button.setEnabled(has_version)
            page.stage_label.setText("Listo.")

        busy_property = busy
        if bool(page.play_button.property("busy")) != busy_property:
            page.play_button.setProperty("busy", busy_property)
            repolish(page.play_button)

    def _set_status(self, text: str, kind: str = "normal") -> None:
        # La barra de estado se construye despues de las paginas; una
        # señal temprana no debe romper el arranque.
        if not hasattr(self, "status_label"):
            return
        mapping = {"normal": "statusLabel", "error": "statusError",
                   "ok": "statusOk"}
        self.status_label.setText(text)
        self.status_label.setObjectName(mapping.get(kind, "statusLabel"))
        repolish(self.status_label)
        if hasattr(self, "status_dot"):
            dot_kind = kind if kind in ("ok", "error") else "normal"
            if self.status_dot.property("kind") != dot_kind:
                self.status_dot.setProperty("kind", dot_kind)
                repolish(self.status_dot)

    def _set_progress(self, done: int, total: int) -> None:
        if not hasattr(self, "progress"):
            return
        page = getattr(self, "play_page", None)
        if page is not None:
            page.set_progress_visible(True)
        if total <= 0:
            self.progress.setRange(0, 0)
            self.percent_label.setText("")
            return
        self.progress.setRange(0, total)
        self.progress.setValue(min(done, total))
        self.percent_label.setText(f"{int(done * 100 / total)}%")

    def _hide_progress(self) -> None:
        page = getattr(self, "play_page", None)
        if page is not None:
            page.set_progress_visible(False)

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
                and not self.play_page.version_picker.count():
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
        worker = ManifestWorker(self.settings.show_all_versions,
                                getattr(self.settings, "offline_mode", False),
                                self)
        worker.ready.connect(self._on_manifest_ready)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(self._on_manifest_finished)
        self._manifest_worker = worker
        worker.start()

    def _on_manifest_ready(self, entries: list[dict]) -> None:
        self._entries = entries
        picker = self.play_page.version_picker
        for entry in entries:
            if entry.get("local"):
                payload = load_version_profile(entry["id"]) or {}
                entry["base"] = payload.get("inheritsFrom") or entry["id"]
            else:
                entry["base"] = entry["id"]
        picker.set_entries(entries)

        current = self.settings.version
        ids = {entry["id"] for entry in entries}
        choice = ""
        if current in ids:
            choice = current
        else:
            # Preferir una version ya descargada (juego inmediato).
            installed = sorted(local_profiles(),
                               key=parse_version_key, reverse=True)
            for profile_id in installed:
                if profile_id in ids:
                    choice = profile_id
                    break
            if not choice and entries:
                # La release mas reciente; con snapshots activados el
                # primero puede ser una pre-release y no interesa por defecto.
                choice = next(
                    (e["id"] for e in entries if e.get("type") == "release"),
                    entries[0]["id"])
        if choice:
            picker.select(choice)
            self.settings.version = choice
        self._update_version_meta()
        self._refresh_state()
        if not entries:
            self._set_status("Sin versiones disponibles.", "error")
        else:
            self._set_status("Listo.", "ok")

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
        self.play_page._refresh_mods_status()
        if not self._is_busy():
            self._set_status("Listo.", "normal")

    def _update_version_meta(self) -> None:
        version_id = self._selected_version()
        if not version_id:
            self.play_page.version_meta.setText("Sin versiones cargadas.")
            return
        payload = load_version_profile(version_id) or {}
        base = payload.get("inheritsFrom") or version_id
        loader = loader_kind(version_id)
        kind = {"optifine": "OptiFine", "neoforge": "NeoForge",
                "fabric": "Fabric", "forge": "Forge"}.get(
                    loader, "Perfil local" if payload.get("inheritsFrom")
                    else "Vanilla")
        if paths.find_version_jar(base) is not None:
            state = "instalada"
        else:
            state = "descarga al jugar"
        # El picker ya muestra el id; aqui solo va el resumen util.
        self.play_page.version_meta.setText(
            f"Java {_java_major_display(version_id, payload)} · "
            f"{kind} · {state}"
        )
        self._update_optifine_row(base)

    def _local_profile_ids(self) -> list[str]:
        """Ids de perfiles locales; usa los entries ya cargados si hay."""
        entries = getattr(self, "_entries", None)
        if entries:
            return [entry["id"] for entry in entries if entry.get("local")]
        return local_profiles()

    def _update_optifine_row(self, base: str) -> None:
        profiles = [pid for pid in self._local_profile_ids()
                    if base and pid.startswith(f"{base}-OptiFine_")]
        if profiles:
            edition = profiles[0].split("OptiFine_", 1)[-1].replace("_", " ")
            self.play_page.optifine_status.setText(f"Instalado · {edition}")
            self.play_page.optifine_button.setText("Reinstalar…")
        else:
            self.play_page.optifine_status.setText("No instalado")
            self.play_page.optifine_button.setText("Instalar…")

    # --------------------------------------------------------------- juego
    def play_version(self, version_id: str) -> None:
        """Lanza directamente una version instalada (desde Versiones)."""
        if self._is_busy():
            return
        picker = self.play_page.version_picker
        picker.ensure_entry(version_id)
        picker.select(version_id)
        self.settings.version = version_id
        self._on_version_changed()
        self._on_play_clicked()

    def delete_version(self, version_id: str) -> None:
        if self._is_busy():
            return
        target = paths.version_dir(version_id)
        if not target.exists():
            return
        answer = QMessageBox.question(
            self, "Eliminar versión",
            f"Se eliminará '{version_id}' (cliente, perfil y nativos). "
            "Las librerías y assets compartidos se conservan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            shutil.rmtree(target)
        except OSError as error:
            QMessageBox.warning(self, "No se pudo eliminar la versión",
                                str(error))
            return
        self.console.append(f"Versión eliminada: {version_id}")
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

        # Mods incompatibles se apartan un momento (mods/.azero-disabled/)
        # y se restauran al terminar el juego: el arranque no falla.
        mods.restore_quarantined()
        if not self._quarantine_incompatible_mods(version_id):
            return

        self.settings.version = version_id
        self._save_settings()
        shown_name = name if online else self.settings.username.strip()
        self.console.append(f"=== {version_id} · {shown_name} ===")

        # Aviso de primera ejecución: descarga + arranque pueden tardar.
        base = self._selected_base() or version_id
        needs_download = paths.find_version_jar(base) is None
        if needs_download and base not in self._launch_notices_shown:
            self._launch_notices_shown.add(base)
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Icon.Information)
            box.setWindowTitle("Primera ejecución")
            box.setText(
                f"Minecraft {base} se descargará ahora "
                "(cliente, librerías y assets).")
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            # No modal: el lanzamiento continúa mientras se lee.
            box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            box.show()
        self._set_launch_notice(
            "Descarga inicial en curso; puede tardar varios minutos."
            if needs_download else "")
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

    def _set_launch_notice(self, text: str) -> None:
        """Muestra/oculta el aviso contextual bajo la etapa de arranque."""
        label = getattr(self.play_page, "launch_notice", None)
        if label is None:
            return
        label.setText(text)
        label.setVisible(bool(text))

    def _on_launched(self, pid: int, log_path: str, auto_close: bool) -> None:
        self._set_progress(1, 1)
        self._set_status(f"Minecraft iniciado (PID {pid}).", "ok")
        self._set_launch_notice("")
        self.console.append(f"Minecraft iniciado · PID {pid}")
        self.console.append(f"Log del juego: {log_path}")
        self.stage_label.setText("En ejecución.")
        version_id = self._selected_version() or self.settings.version
        base = self._selected_base() or version_id
        jar_path = (paths.find_version_jar(base)
                    or paths.version_jar_path(base))
        size = jar_path.stat().st_size if jar_path.exists() else 0
        database.log_download(
            "version", f"Cliente {version_id} listo",
            version_id=version_id, size_bytes=size, status="ok",
            detail=f"Sesión con {self._session_name}")
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
        self._set_launch_notice("")
        self.console.append(f"Minecraft finalizó (código {code}).")
        if self._session_id is not None:
            database.session_end(self._session_id, exit_code=code)
            self._session_id = None
            self.versions_page.refresh_all()
        self._restore_quarantined_mods()
        self._hide_progress()
        if not self._allow_close:
            self._set_status(f"Juego cerrado (código {code}).", "normal")

    def _on_failed(self, message: str) -> None:
        self._set_launch_notice("")
        self.console.append(f"ERROR: {message}")
        database.log_download(
            "error", message.strip().splitlines()[0]
            if message.strip() else "Error desconocido",
            version_id=self._selected_version() or self.settings.version,
            status="error")
        if self._session_id is not None:
            database.session_end(self._session_id, detail="error")
            self._session_id = None
        self._restore_quarantined_mods()
        first_line = (message.strip().splitlines()[0]
                      if message.strip() else "Error desconocido")
        self._set_status("No se pudo iniciar el juego.", "error")
        self._set_progress(0, 1)
        self._hide_progress()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("No se pudo iniciar Minecraft")
        box.setText(first_line)
        box.setInformativeText(
            "Revisa el registro completo y vuelve a intentarlo."
        )
        box.setDetailedText(message)
        box.exec()

    def _on_cancelled(self) -> None:
        self._set_launch_notice("")
        self.console.append("Operación cancelada.")
        if self._session_id is not None:
            database.session_end(self._session_id, detail="cancelado")
            self._session_id = None
        self._restore_quarantined_mods()
        self._set_progress(0, 1)
        self._hide_progress()
        self._set_status("Operación cancelada.", "normal")

    def _on_launch_finished(self) -> None:
        worker = self._launch_worker
        self._launch_worker = None
        if worker:
            worker.deleteLater()
        self._hide_progress()
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
                "de versiones y vuelve a intentarlo.",
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
        self._hide_progress()
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
            _apply_titlebar_theme(self, theme.current_theme_name() == "dark")

    def closeEvent(self, event) -> None:  # noqa: N802 - API de Qt
        try:
            self.settings.win_geometry = bytes(
                self.saveGeometry().toBase64()).decode("ascii")
        except Exception:  # noqa: BLE001
            pass
        settings_page = getattr(self, "settings_page", None)
        if settings_page is not None:
            try:
                settings_page.save_if_dirty()
            except Exception:  # noqa: BLE001 - nunca impedir el cierre
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
        settings_page = getattr(self, "settings_page", None)
        forge_worker = getattr(settings_page, "_forge_worker", None)
        loader_worker = getattr(settings_page, "_loader_worker", None)
        for worker in (forge_worker, loader_worker):
            if worker is not None and worker.isRunning():
                worker.cancel()
                worker.wait(1500)
        # Los workers que siguen vivos (p. ej. el juego en curso, que el
        # worker solo vigila) no pueden destruirse en ejecucion: se despegan
        # del arbol de widgets y Qt los libera al terminar el proceso.
        workers = [self._manifest_worker, self._launch_worker,
                   self._of_worker,
                   getattr(getattr(self, "account_page", None),
                           "_login_worker", None),
                   getattr(getattr(self, "about_page", None),
                           "_update_checker", None),
                   forge_worker, loader_worker]
        for worker in workers:
            if worker is not None and worker.isRunning():
                worker.setParent(None)
                worker.finished.connect(worker.deleteLater)
        # Si habia mods en cuarentena y NO hay partida en curso, vuelven
        # a mods/. Con partida activa se espera: restaurar demasiado
        # pronto (p. ej. autocierre nada mas spawnear) podria hacer que
        # el loader lea los mods incompatibles al escanear mods/.
        if self._session_id is None:
            try:
                mods.restore_quarantined()
            except Exception:  # noqa: BLE001 - nunca impedir el cierre
                pass
        super().closeEvent(event)
