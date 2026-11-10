"""Páginas de la interfaz: Jugar, Versiones, Cuenta, Ajustes y Acerca de."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import MainWindow

from PyQt6.QtCore import Qt, QThread, QTimer, QUrl, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                             QDialog, QFileDialog, QFormLayout, QFrame,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMessageBox,
                             QProgressBar, QPushButton, QSizePolicy,
                             QSpinBox, QTableWidget,
                             QTableWidgetItem, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import (APP_NAME, APP_VERSION, database, forge, hardware,
                java as java_module, loaders, mcscan, mods, msauth, paths)
from ..auth import offline_uuid, validate_username
from ..constants import (DOCS_URL, ISSUES_URL, LATEST_RELEASE_API,
                         MEMORY_STEP_MB, MIN_MEMORY_MB, RELEASES_URL,
                         REPO_URL, SPONSORS_URL, USER_AGENT)
from ..manifest import (load_version_profile, local_profiles,
                        parse_version_key, version_family_label)
from ..util import human_size
from ..workers import (ForgeInstallWorker, LoaderInstallWorker,
                       MSLoginWorker)
from . import theme
from .widgets import (Avatar, Card, ConsoleView, Divider,
                      FocusWheelSlider, InfoGrid, PageHeader, Pill,
                      ScrollPage, StatCard, VersionPicker, faint_label,
                      link_button, list_row, make_button, muted_label,
                      repolish, section_label, set_empty_table_message)


def _gb_text(memory_mb: int) -> str:
    value = memory_mb / 1024
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text} GB"


def _ram_text(memory_mb: int) -> str:
    """Etiqueta precisa de RAM: MB exactos + equivalente en GB."""
    return f"{memory_mb} MB · {_gb_text(memory_mb)}"


def _fmt_time(ts: float | None) -> str:
    if not ts:
        return "-"
    return time.strftime("%d/%m/%Y %H:%M", time.localtime(ts))


def _fmt_duration(start: float, end: float | None) -> str:
    if not end:
        return "en curso"
    seconds = max(0, int(end - start))
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {sec}s"
    return f"{sec}s"


def _open_path(path: Path) -> None:
    paths.ensure_dirs()
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


# ================================================================ JUGAR
class PlayPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._ram_presets: list[tuple[QPushButton, int]] = []
        self._build()

    # ------------------------------------------------------------- build
    def _build(self) -> None:
        header = PageHeader(
            "Jugar", "Perfil, versión y memoria del juego.")
        self.body.addWidget(header)

        columns = QHBoxLayout()
        columns.setSpacing(theme.COLUMN_GAP)

        left = QWidget()
        left.setMinimumWidth(300)
        left.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(theme.CARD_SPACING)

        left_layout.addWidget(self._account_card())
        left_layout.addWidget(self._version_card())

        self.play_button = make_button("JUGAR", "primary")
        self.play_button.setObjectName("playButton")
        self.play_button.setMinimumHeight(46)
        self.play_button.setToolTip("Iniciar el juego (Ctrl+Enter)")
        self.play_button.setAccessibleName("Jugar")
        self.play_button.setAccessibleDescription(
            "Inicia Minecraft con el perfil y la versión seleccionados")
        self.play_button.clicked.connect(self.shell._on_play_clicked)
        left_layout.addWidget(self.play_button)

        left_layout.addWidget(self._quick_card())
        left_layout.addStretch(1)
        columns.addWidget(left, 2)

        console_card = Card()
        console_head = QHBoxLayout()
        console_head.setSpacing(6)
        console_head.addWidget(section_label("Registro"))
        console_head.addStretch(1)
        console_head.addWidget(make_button(
            "Carpeta", "ghost", "Abrir la carpeta .minecraft",
            self.shell._open_mc_folder))
        console_head.addWidget(make_button(
            "Copiar", "ghost", "Copia todo el registro al portapapeles",
            self._copy_console))
        console_head.addWidget(make_button(
            "Guardar…", "ghost", "Guarda el registro en un archivo de texto",
            self._save_console))
        console_head.addWidget(make_button(
            "Limpiar", "ghost", "Vaciar el registro (Ctrl+L)",
            lambda: self.console.clear()))
        console_card.body.addLayout(console_head)

        self.console = ConsoleView()
        self.console.setMinimumHeight(140)
        console_card.body.addWidget(self.console, 1)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(8)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        self.percent_label = faint_label("")
        self.percent_label.setFixedWidth(42)
        self.set_progress_visible(False)
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.percent_label)
        console_card.body.addLayout(progress_row)

        stage_row = QHBoxLayout()
        stage_row.setSpacing(8)
        self.stage_label = muted_label("Esperando acción.")
        self.stage_label.setWordWrap(True)
        stage_row.addWidget(self.stage_label, 1)
        console_card.body.addLayout(stage_row)

        self.launch_notice = muted_label("")
        self.launch_notice.setWordWrap(True)
        self.launch_notice.setVisible(False)
        console_card.body.addWidget(self.launch_notice)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(theme.CARD_SPACING)
        right_layout.addWidget(console_card, 1)
        columns.addWidget(right, 3)
        self.body.addLayout(columns, 1)

    def _copy_console(self) -> None:
        """Copia el contenido completo del registro al portapapeles."""
        text = self.console.toPlainText()
        if text.strip():
            QApplication.clipboard().setText(text)
            self.shell._set_status("Registro copiado al portapapeles.", "ok")

    def _save_console(self) -> None:
        """Guarda el registro visible en un archivo de texto UTF-8."""
        text = self.console.toPlainText()
        if not text.strip():
            self.shell._set_status("El registro está vacío.", "error")
            return
        target, _ = QFileDialog.getSaveFileName(
            self, "Guardar registro", "azero-registro.txt",
            "Archivos de texto (*.txt);;Todos los archivos (*)")
        if not target:
            return
        try:
            Path(target).write_text(text, encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(
                self, "No se pudo guardar el registro", str(error))
            return
        self.shell._set_status(f"Registro guardado en {target}", "ok")

    def set_progress_visible(self, visible: bool) -> None:
        """Muestra el progreso solo mientras hay una operación activa."""
        self.progress.setVisible(visible)
        self.percent_label.setVisible(visible)

    def _account_card(self) -> Card:
        card = Card()
        card.body.addWidget(section_label("Jugador"))
        row = QHBoxLayout()
        row.setSpacing(14)
        self.avatar = Avatar(48)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(3)

        self.name_edit = QLineEdit(self.shell.settings.username)
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setMaxLength(16)
        self.name_edit.setPlaceholderText("Nombre de jugador")
        self.name_edit.setToolTip(
            "Nombre offline de 3 a 16 caracteres (letras, números y _).")
        self.name_edit.textChanged.connect(self.shell._on_username_changed)

        self.account_label = QLabel()
        self.account_label.setObjectName("valueLabel")
        self.account_label.setVisible(False)

        self.uuid_label = QLabel()
        self.uuid_label.setObjectName("mono")
        self.uuid_label.setWordWrap(True)

        column.addWidget(self.name_edit)
        column.addWidget(self.account_label)
        column.addWidget(self.uuid_label)
        row.addWidget(self.avatar)
        row.addLayout(column, 1)
        row.addWidget(make_button(
            "Cambiar", "ghost", "Cambiar de cuenta",
            lambda: self.shell._go_page(2)), 0,
            Qt.AlignmentFlag.AlignVCenter)
        card.body.addLayout(row)
        return card

    def _version_card(self) -> Card:
        card = Card()
        card.body.addWidget(section_label("Versión"))
        self.version_picker = VersionPicker()
        self.version_picker.set_placeholder("Cargando versiones…")
        self.version_picker.setToolTip(
            "Versiones agrupadas por loader, familia y versión base")
        self.version_picker.selectionChanged.connect(
            self.shell._on_version_changed)
        card.body.addWidget(self.version_picker)

        self.version_meta = muted_label(
            "Leyendo el manifiesto oficial de Mojang…")
        self.version_meta.setWordWrap(True)
        card.body.addWidget(self.version_meta)
        card.body.addWidget(Divider())

        row = QHBoxLayout()
        row.setSpacing(10)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        title = QLabel("OptiFine")
        title.setObjectName("valueLabel")
        self.optifine_status = faint_label("Comprobando estado…")
        self.optifine_status.setWordWrap(True)
        column.addWidget(title)
        column.addWidget(self.optifine_status)
        self.optifine_button = make_button(
            "Instalar…", "accent",
            "Instala el parche oficial sin abrir ventanas",
            self.shell._on_install_optifine)
        row.addLayout(column, 1)
        row.addWidget(self.optifine_button)
        card.body.addLayout(row)
        card.body.addWidget(Divider())

        mods_row = QHBoxLayout()
        mods_row.setSpacing(10)
        mods_col = QVBoxLayout()
        mods_col.setContentsMargins(0, 0, 0, 0)
        mods_col.setSpacing(2)
        mods_title = QLabel("Mods")
        mods_title.setObjectName("valueLabel")
        self.mods_status = faint_label("")
        self.mods_status.setWordWrap(True)
        mods_col.addWidget(mods_title)
        mods_col.addWidget(self.mods_status)
        mods_row.addLayout(mods_col, 1)
        self.manage_mods_button = make_button(
            "Gestionar", "ghost",
            "Abrir Ajustes › Mods",
            lambda: self.shell._go_page(3))
        mods_row.addWidget(self.manage_mods_button)
        card.body.addLayout(mods_row)
        self._refresh_mods_status()
        return card

    def _refresh_mods_status(self) -> None:
        installed = mods.list_mods()
        if not installed:
            self.mods_status.setText("Sin mods")
            return
        loader_mods = [mod for mod in installed if mod.loader]
        count = len(installed)
        parts = [f"{count} mod" + ("s" if count != 1 else "")]
        kinds = sorted({mod.loader for mod in loader_mods})
        if kinds:
            parts.append(", ".join(kind.capitalize() for kind in kinds))
        text = " · ".join(parts)
        version_id = (self.shell._selected_version() or "").lower()
        missing = [kind for kind in kinds
                   if kind not in version_id
                   and not loaders.has_loader_profile(kind)]
        if missing:
            text += " · falta " + ", ".join(
                kind.capitalize() for kind in missing)
        # Mods que declaran una version de Minecraft incompatible.
        base = self.shell._selected_base() or ""
        if base:
            bad = mods.incompatible_mods(installed, base)
            if bad:
                names = ", ".join(
                    mod.title or mod.name for mod, _dep in bad[:3])
                extra = f" +{len(bad) - 3}" if len(bad) > 3 else ""
                text += f" · {names}{extra} no es para MC {base}"
        self.mods_status.setText(text)

    def _quick_card(self) -> Card:
        card = Card()

        head = QHBoxLayout()
        head.setSpacing(8)
        head.addWidget(faint_label("Memoria RAM"))
        self.ram_value = QLabel(_ram_text(self.shell.settings.memory_mb))
        self.ram_value.setObjectName("valueLabel")
        head.addWidget(self.ram_value)
        head.addStretch(1)
        head.addWidget(make_button(
            "Consejos", "ghost", "Recomendaciones de RAM, GC y mods",
            lambda: TipsDialog(self).exec()))
        card.body.addLayout(head)

        self.ram_slider = FocusWheelSlider(Qt.Orientation.Horizontal)
        ram_max = hardware.memory_slider_max_mb()
        self.ram_slider.setMinimum(MIN_MEMORY_MB)
        self.ram_slider.setMaximum(ram_max)
        self.ram_slider.setSingleStep(MEMORY_STEP_MB)
        self.ram_slider.setPageStep(1024)
        self.ram_slider.setToolTip(
            f"Máximo recomendado: {_gb_text(ram_max)}. Asignar más RAM de "
            "la disponible ralentiza el equipo y puede cerrar el juego.")
        self.ram_slider.valueChanged.connect(self.shell._on_ram_changed)
        self.ram_slider.valueChanged.connect(self._sync_ram_presets)
        self.ram_slider.sliderReleased.connect(self._commit_ram)
        card.body.addWidget(self.ram_slider)

        presets = QHBoxLayout()
        presets.setSpacing(6)
        recommended = hardware.recommended_memory_mb()
        for label, mb in (("2 GB", 2048), ("4 GB", 4096),
                          ("Recomendado", recommended),
                          ("Máx", ram_max)):
            button = make_button(
                label, "preset", f"Asignar {mb} MB de RAM al juego")
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, value=mb: self._apply_ram_preset(value))
            self._ram_presets.append((button, mb))
            presets.addWidget(button)
        presets.addStretch(1)
        card.body.addLayout(presets)

        card.body.addWidget(faint_label("Servidor"))
        self.server_edit = QLineEdit(self.shell.settings.server)
        self.server_edit.setPlaceholderText(
            "play.ejemplo.net:25565")
        self.server_edit.setClearButtonEnabled(True)
        self.server_edit.setToolTip(
            "Conexión automática al iniciar. Vacío = menú multijugador.")
        self.server_edit.editingFinished.connect(
            self.shell._on_server_changed)
        card.body.addWidget(self.server_edit)

        self.auto_close_check = QCheckBox(
            "Cerrar al iniciar el juego")
        self.auto_close_check.setChecked(self.shell.settings.auto_close)
        self.auto_close_check.setToolTip(
            "El juego corre en un proceso independiente: el launcher "
            "puede cerrarse y liberar su memoria.")
        self.auto_close_check.toggled.connect(
            self.shell._on_auto_close_changed)
        card.body.addWidget(self.auto_close_check)
        self._sync_ram_presets()
        return card

    def _apply_ram_preset(self, mb: int) -> None:
        """Preset de RAM: mueve el slider y guarda el ajuste."""
        self.ram_slider.setValue(mb)
        self.shell._save_settings()
        self._sync_ram_presets()

    def _commit_ram(self) -> None:
        """Ajusta la RAM a pasos de 512 MB al soltar el slider."""
        value = self.ram_slider.value()
        snapped = round(value / MEMORY_STEP_MB) * MEMORY_STEP_MB
        snapped = max(self.ram_slider.minimum(),
                      min(self.ram_slider.maximum(), snapped))
        if snapped != value:
            self.ram_slider.setValue(snapped)
        self.shell._save_settings()

    def _sync_ram_presets(self, *_) -> None:
        """Marca un único preset: el que coincide con el slider."""
        value = self.ram_slider.value()
        matched = False
        for button, mb in self._ram_presets:
            is_match = mb == value and not matched
            button.setChecked(is_match)
            matched = matched or is_match

    # ------------------------------------------------------------ estado
    def refresh_account(self, name: str, uuid_: str, kind: str,
                        online: bool) -> None:
        self.avatar.set_identity(name or "?", uuid_ or name or "?")
        self.uuid_label.setText(f"UUID {uuid_}" if uuid_
                                else "UUID pendiente")
        self.name_edit.setVisible(not online)
        self.account_label.setVisible(online)
        if online:
            self.account_label.setText(name)
        self.uuid_label.setToolTip(
            "Cuenta oficial de Minecraft" if online
            else "UUID offline v3 (Java nameUUIDFromBytes)")

    def showEvent(self, event) -> None:  # noqa: N802 - API de Qt
        super().showEvent(event)
        self._refresh_mods_status()

    def set_busy_widgets(self, busy: bool) -> None:
        widgets: list[QWidget] = [
            self.name_edit, self.version_picker, self.ram_slider,
            self.auto_close_check, self.server_edit, self.optifine_button,
            self.manage_mods_button,
        ]
        widgets.extend(button for button, _ in self._ram_presets)
        for widget in widgets:
            widget.setEnabled(not busy)


# ============================================================= VERSIONES
class VersionsPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._build()

    def _build(self) -> None:
        header = PageHeader(
            "Versiones", "Perfiles instalados, descargas y sesiones.")
        header.add_action(make_button(
            "Actualizar", "accent", "Volver a leer versiones e historial (F5)",
            self.refresh_all))
        header.add_action(make_button(
            "Limpiar", "danger",
            "Borrar descargas y sesiones registradas",
            self.clear_history))
        self.body.addWidget(header)

        stats = QHBoxLayout()
        stats.setSpacing(theme.COLUMN_GAP)
        self.stat_versions = StatCard("Versiones", "0")
        self.stat_size = StatCard("Tamaño", "0 MB")
        self.stat_sessions = StatCard("Partidas", "0")
        stats.addWidget(self.stat_versions, 1)
        stats.addWidget(self.stat_size, 1)
        stats.addWidget(self.stat_sessions, 1)
        self.body.addLayout(stats)

        installed_card = Card()
        installed_card.body.addWidget(section_label("Versiones instaladas"))
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filtrar por nombre o versión…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setToolTip(
            "Filtra la lista por nombre de versión o grupo.")
        self.filter_edit.textChanged.connect(self._apply_filter)
        filters.addWidget(self.filter_edit, 1)
        self.type_filter = QComboBox()
        self.type_filter.addItem("Todos los tipos", "all")
        self.type_filter.addItem("Vanilla", "Vanilla")
        self.type_filter.addItem("Forge", "Forge")
        self.type_filter.addItem("Fabric", "Fabric")
        self.type_filter.addItem("NeoForge", "NeoForge")
        self.type_filter.addItem("OptiFine", "OptiFine")
        self.type_filter.setFixedWidth(150)
        self.type_filter.setToolTip("Mostrar solo un tipo de perfil")
        self.type_filter.currentIndexChanged.connect(self._apply_filter)
        filters.addWidget(self.type_filter)
        installed_card.body.addLayout(filters)

        self.installed_list = QTreeWidget()
        self.installed_list.setColumnCount(1)
        self.installed_list.setHeaderHidden(True)
        self.installed_list.setRootIsDecorated(True)
        self.installed_list.setIndentation(14)
        self.installed_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.installed_list.setUniformRowHeights(False)
        self.installed_list.setMinimumHeight(190)
        self.installed_list.setMaximumHeight(420)
        self.installed_list.setExpandsOnDoubleClick(False)
        self.installed_list.setToolTip(
            "Pulsa un grupo para plegarlo o desplegarlo.")
        self.installed_list.itemClicked.connect(self._on_tree_clicked)
        self.installed_list.itemExpanded.connect(self._on_group_toggled)
        self.installed_list.itemCollapsed.connect(self._on_group_toggled)
        installed_card.body.addWidget(self.installed_list)

        self.filter_empty = QLabel("Sin resultados para este filtro.")
        self.filter_empty.setObjectName("emptyState")
        self.filter_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filter_empty.setMinimumHeight(190)
        self.filter_empty.setVisible(False)
        installed_card.body.addWidget(self.filter_empty)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch(1)
        row.addWidget(make_button(
            "Añadir carpeta…", "accent",
            "Registrar otra carpeta .minecraft y sus versiones",
            self._add_mc_folder))
        row.addWidget(make_button(
            "Abrir .minecraft", "ghost", "Abrir la carpeta oficial",
            lambda: _open_path(paths.MC_DIR)))
        row.addWidget(make_button(
            "Registros", "ghost", "Abrir la carpeta de registros",
            lambda: _open_path(paths.LOGS_DIR)))
        installed_card.body.addLayout(row)
        self.extra_roots_label = faint_label("")
        installed_card.body.addWidget(self.extra_roots_label)
        self.body.addWidget(installed_card)

        downloads_card = Card()
        downloads_card.body.addWidget(
            section_label("Historial de operaciones"))
        self.downloads_table = self._make_table(
            ["Fecha", "Tipo", "Detalle", "Versión", "Tamaño", "Estado"], 2)
        self.downloads_table.setMinimumHeight(130)
        self.downloads_table.setMaximumHeight(220)
        downloads_card.body.addWidget(self.downloads_table)
        self.body.addWidget(downloads_card)

        sessions_card = Card()
        sessions_card.body.addWidget(section_label("Sesiones recientes"))
        self.sessions_table = self._make_table(
            ["Inicio", "Jugador", "Versión", "Cuenta", "Duración", "Estado"], 1)
        self.sessions_table.setMinimumHeight(120)
        self.sessions_table.setMaximumHeight(200)
        sessions_card.body.addWidget(self.sessions_table)
        self.body.addWidget(sessions_card)

        self.body.addStretch(1)

    def _make_table(self, headers: list[str],
                    stretch_column: int = 1) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        for column in range(len(headers)):
            mode = (QHeaderView.ResizeMode.Stretch
                    if column == stretch_column
                    else QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(column, mode)
        table.setShowGrid(False)
        return table

    # ------------------------------------------------------------ datos
    def refresh_all(self) -> None:
        installed = self._scan_installed()
        self._refresh_stats(installed)
        self._refresh_installed(installed)
        self._refresh_downloads()
        self._refresh_sessions()

    def _refresh_stats(self, installed: list[dict]) -> None:
        total = sum(item["size"] for item in installed)
        self.stat_versions.set_value(str(len(installed)))
        self.stat_size.set_value(human_size(total))
        sessions = database.list_sessions(limit=500)
        played = sum(1 for s in sessions if s.get("ended"))
        self.stat_sessions.set_value(str(played))

    def _scan_installed(self) -> list[dict]:
        entries = []
        seen: set[str] = set()
        for versions_dir in paths.versions_dirs():
            try:
                children = sorted(versions_dir.iterdir())
            except OSError:
                continue
            for child in children:
                if not child.is_dir() or child.name in seen:
                    continue
                jar = child / f"{child.name}.jar"
                profile = child / f"{child.name}.json"
                if not jar.exists() and not profile.exists():
                    continue
                seen.add(child.name)
                size = jar.stat().st_size if jar.exists() else 0
                kind = {"optifine": "OptiFine", "neoforge": "NeoForge",
                        "fabric": "Fabric", "forge": "Forge"}.get(
                    loaders.loader_kind(child.name), "Vanilla")
                # Los perfiles con herencia no tienen jar propio: el
                # cliente base se descarga bajo demanda al jugar.
                entries.append({
                    "id": child.name, "size": size, "kind": kind,
                    "client": jar.exists(),
                })
        entries.sort(key=lambda e: parse_version_key(e["id"]), reverse=True)
        return entries

    def _add_mc_folder(self) -> None:
        """Escanea una carpeta elegida por el usuario y registra su
        raíz .minecraft para reconocer sus versiones y perfiles Forge."""
        folder = QFileDialog.getExistingDirectory(
            self, "Carpeta con Minecraft (o su carpeta contenedora)")
        if not folder:
            return
        root = mcscan.detect_mc_root(folder)
        if root is None:
            QMessageBox.information(
                self, "Escáner de Minecraft",
                "No se encontró una carpeta .minecraft válida. Elige la "
                "carpeta .minecraft o una que la contenga.")
            return
        settings = self.shell.settings
        current = [line.strip()
                   for line in settings.extra_mc_dirs.splitlines()
                   if line.strip()]
        if root == paths.MC_DIR or str(root) in current:
            self.shell._set_status(
                f"La carpeta ya está registrada: {root}", "ok")
            return
        current.append(str(root))
        settings.extra_mc_dirs = "\n".join(current)
        paths.set_extra_mc_dirs(current)
        self.shell._save_settings()
        self.shell._reload_versions()
        self.refresh_all()
        self.shell._set_status(
            f"Carpeta de Minecraft registrada: {root}", "ok")

    def _refresh_installed(self, installed: list[dict]) -> None:
        self.installed_list.clear()
        groups: dict[str, QTreeWidgetItem] = {}
        for entry in installed:
            # Los perfiles con herencia (Forge/OptiFine) se agrupan bajo
            # su versión base, no bajo su nombre de perfil.
            payload = load_version_profile(entry["id"]) or {}
            base = payload.get("inheritsFrom") or entry["id"]
            group_label = version_family_label(base)
            group = groups.get(group_label)
            if group is None:
                group = QTreeWidgetItem([group_label])
                group.setFlags(Qt.ItemFlag.ItemIsEnabled)
                group.setData(0, Qt.ItemDataRole.UserRole, group_label)
                group.setSizeHint(0, QSize(0, 26))
                group.setForeground(0, QColor(theme.COLORS["TEXT_DIM"]))
                font = group.font(0)
                font.setBold(True)
                font.setPointSizeF(8.5)
                group.setFont(0, font)
                self.installed_list.addTopLevelItem(group)
                groups[group_label] = group

            row, layout = list_row()
            info = QVBoxLayout()
            info.setContentsMargins(0, 0, 0, 0)
            info.setSpacing(1)
            name = QLabel(entry["id"])
            name.setObjectName("valueLabel")
            parts = [human_size(entry["size"])] if entry["size"] else []
            if not entry["client"]:
                parts.append("cliente bajo demanda")
            detail = QLabel(" · ".join(parts) or "perfil local")
            detail.setObjectName("faint")
            info.addWidget(name)
            info.addWidget(detail)
            layout.addLayout(info, 1)
            layout.addWidget(Pill(entry["kind"], dim=True))

            play = make_button(
                "Jugar", "primary", "Iniciar esta versión",
                lambda vid=entry["id"]: self.shell.play_version(vid))
            if not entry["client"]:
                play.setToolTip(
                    "Perfil sin cliente propio: el cliente base se "
                    "descargará al jugar.")
            folder = make_button(
                "Carpeta", "ghost", "Abrir la carpeta de esta versión",
                lambda vid=entry["id"]: _open_path(
                    paths.find_version_dir(vid) or paths.version_dir(vid)))
            delete = make_button(
                "Eliminar", "danger",
                "Eliminar los archivos de esta versión",
                lambda vid=entry["id"]: self.shell.delete_version(vid))
            layout.addWidget(play)
            layout.addWidget(folder)
            layout.addWidget(delete)

            row.ensurePolished()
            item = QTreeWidgetItem()
            item.setData(0, Qt.ItemDataRole.UserRole, entry["id"])
            item.setData(0, int(Qt.ItemDataRole.UserRole) + 1,
                         entry["kind"])
            item.setSizeHint(0, row.sizeHint())
            group.addChild(item)
            self.installed_list.setItemWidget(item, 0, row)

        for group in groups.values():
            group.setExpanded(True)
            group.setText(0, self._group_label_text(group))

        if self.installed_list.topLevelItemCount() == 0:
            item = QTreeWidgetItem(
                ["No hay versiones instaladas. Elige una en Jugar para "
                 "descargarla."])
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.installed_list.addTopLevelItem(item)
        self._apply_filter()
        extra = [line.strip()
                 for line in self.shell.settings.extra_mc_dirs.splitlines()
                 if line.strip()]
        self.extra_roots_label.setText(
            "Carpetas adicionales: " + " · ".join(extra) if extra else "")

    def _group_label_text(self, group: QTreeWidgetItem) -> str:
        """Texto del grupo con conteo visible y cheurón de estado."""
        label = str(group.data(0, Qt.ItemDataRole.UserRole) or "")
        total = group.childCount()
        visible = sum(1 for index in range(total)
                      if not group.child(index).isHidden())
        prefix = "▾" if group.isExpanded() else "▸"
        if visible == total:
            unit = "versión" if total == 1 else "versiones"
            return f"{prefix}  {label}  ·  {total} {unit}"
        return f"{prefix}  {label}  ·  {visible} de {total}"

    def _on_group_toggled(self, item: QTreeWidgetItem) -> None:
        if item.childCount():
            item.setText(0, self._group_label_text(item))
        self._fit_installed_height()

    def _on_tree_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        if item.parent() is None and item.childCount():
            item.setExpanded(not item.isExpanded())

    def _apply_filter(self) -> None:
        """Filtra el árbol por texto y por tipo de perfil."""
        text = self.filter_edit.text().strip().lower()
        kind = (self.type_filter.currentData()
                if hasattr(self, "type_filter") else "all")
        kind = kind or "all"
        any_visible = False
        for i in range(self.installed_list.topLevelItemCount()):
            group = self.installed_list.topLevelItem(i)
            if group.childCount() == 0:
                # Elemento placeholder ("No hay versiones…").
                group.setHidden(bool(text) or kind != "all")
                continue
            visible = 0
            for j in range(group.childCount()):
                child = group.child(j)
                version_id = str(
                    child.data(0, Qt.ItemDataRole.UserRole) or "")
                child_kind = str(
                    child.data(0, int(Qt.ItemDataRole.UserRole) + 1) or "")
                group_key = str(
                    group.data(0, Qt.ItemDataRole.UserRole) or "").lower()
                match = (not text or text in version_id.lower()
                         or text in group_key)
                match = match and (kind == "all" or child_kind == kind)
                child.setHidden(not match)
                visible += 0 if child.isHidden() else 1
            group.setHidden(visible == 0)
            group.setText(0, self._group_label_text(group))
            any_visible = any_visible or visible > 0
        filtered = bool(text) or kind != "all"
        no_results = (filtered and not any_visible
                      and self.installed_list.topLevelItemCount() > 0)
        self.filter_empty.setVisible(no_results)
        self.installed_list.setVisible(not no_results)
        if not no_results:
            self._fit_installed_height()

    def _fit_installed_height(self) -> None:
        """Ajusta el alto de la lista al contenido para no cortar filas."""
        tree = self.installed_list
        tree.doItemsLayout()
        height = 2
        for i in range(tree.topLevelItemCount()):
            group = tree.topLevelItem(i)
            if group.isHidden():
                continue
            height += tree.visualItemRect(group).height()
            if not group.isExpanded():
                continue
            for j in range(group.childCount()):
                child = group.child(j)
                if not child.isHidden():
                    height += tree.visualItemRect(child).height()
        tree.setFixedHeight(min(420, max(190, height)))

    def _refresh_downloads(self) -> None:
        table = self.downloads_table
        table.setRowCount(0)
        rows = database.list_downloads(limit=500)
        if not rows:
            set_empty_table_message(table, "Sin operaciones.")
            return
        for row in rows:
            r = table.rowCount()
            table.insertRow(r)
            values = [
                _fmt_time(row["ts"]),
                row["kind"],
                row["label"],
                row["version_id"] or "-",
                human_size(row["size_bytes"]) if row["size_bytes"] else "-",
                row["status"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setForeground(QColor(theme.COLORS["TEXT_FAINT"]))
                elif c == 5:
                    status = str(value).lower()
                    color = (theme.COLORS["OK_COLOR"] if status == "ok"
                             else theme.COLORS["DANGER"] if status == "error"
                             else theme.COLORS["TEXT_FAINT"])
                    item.setForeground(QColor(color))
                table.setItem(r, c, item)
            table.item(r, 0).setToolTip(
                f"id {row['id']} · {row['kind']} · {row['status']}")

    def _refresh_sessions(self) -> None:
        table = self.sessions_table
        table.setRowCount(0)
        rows = database.list_sessions(limit=500)
        if not rows:
            set_empty_table_message(table, "Sin partidas.")
            return
        for row in rows:
            r = table.rowCount()
            table.insertRow(r)
            ended = row["ended"]
            if ended is None:
                state = "en curso"
                state_color = theme.COLORS["ACCENT"]
            elif row["exit_code"] in (0, None):
                state = "finalizada"
                state_color = theme.COLORS["OK_COLOR"]
            else:
                state = f"código {row['exit_code']}"
                state_color = theme.COLORS["DANGER"]
            if row["detail"]:
                state += f" · {row['detail']}"
            values = [
                _fmt_time(row["started"]),
                row["username"],
                row["version_id"],
                row["account"],
                _fmt_duration(row["started"], ended),
                state,
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 5:
                    item.setForeground(QColor(state_color))
                table.setItem(r, c, item)

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self, "Limpiar historial",
            "Se borrará el historial de descargas y sesiones. "
            "Los archivos del juego no se tocan.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            database.clear_history()
            self.refresh_all()


# ============================================================== CUENTA
class AccountPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._login_worker = None
        self._login_dialog = None
        self._build()

    def _build(self) -> None:
        header = PageHeader(
            "Cuenta", "Perfil offline o cuenta Microsoft.")
        self.body.addWidget(header)

        self.body.addWidget(self._active_card())
        columns = QHBoxLayout()
        columns.setSpacing(theme.COLUMN_GAP)
        columns.addWidget(self._offline_card(), 1,
                          Qt.AlignmentFlag.AlignTop)
        columns.addWidget(self._microsoft_card(), 1,
                          Qt.AlignmentFlag.AlignTop)
        self.body.addLayout(columns)
        self.body.addStretch(1)
        self.refresh_active_summary()

    def _active_card(self) -> Card:
        card = Card()
        head = QHBoxLayout()
        head.addWidget(section_label("Cuenta activa"))
        head.addStretch(1)
        self.active_pill = Pill("OFFLINE", dim=True)
        head.addWidget(self.active_pill)
        card.body.addLayout(head)

        row = QHBoxLayout()
        row.setSpacing(14)
        self.active_avatar = Avatar(54)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        self.active_name = QLabel("—")
        self.active_name.setObjectName("accountName")
        self.active_uuid = QLabel("")
        self.active_uuid.setObjectName("mono")
        self.active_uuid.setWordWrap(True)
        column.addWidget(self.active_name)
        column.addWidget(self.active_uuid)
        row.addWidget(self.active_avatar)
        row.addLayout(column, 1)
        card.body.addLayout(row)
        return card

    def _offline_card(self) -> Card:
        card = Card()
        card.body.addWidget(section_label("Perfil offline"))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.off_avatar = Avatar(54)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(3)
        self.off_name = QLineEdit(self.shell.settings.username)
        self.off_name.setObjectName("nameEdit")
        self.off_name.setMaxLength(16)
        self.off_name.setPlaceholderText("Nombre de jugador")
        self.off_name.textChanged.connect(self._on_offline_name)
        self.off_uuid = QLabel()
        self.off_uuid.setObjectName("mono")
        self.off_uuid.setWordWrap(True)
        column.addWidget(self.off_name)
        column.addWidget(self.off_uuid)
        row.addWidget(self.off_avatar)
        row.addLayout(column, 1)
        card.body.addLayout(row)

        use_row = QHBoxLayout()
        use_row.setSpacing(8)
        use_row.addWidget(make_button(
            "Usar offline", "primary",
            "Jugar con el nombre offline",
            self._use_offline), 1)
        use_row.addWidget(make_button(
            "Copiar UUID", "ghost",
            "Copia el UUID offline al portapapeles",
            self._copy_offline_uuid))
        card.body.addLayout(use_row)
        return card

    def _microsoft_card(self) -> Card:
        card = Card()
        head = QHBoxLayout()
        head.addWidget(section_label("Cuenta Microsoft"))
        head.addStretch(1)
        self.ms_status = Pill("SIN SESIÓN", dim=True)
        head.addWidget(self.ms_status)
        card.body.addLayout(head)

        card.body.addWidget(make_button(
            "Iniciar sesión", "primary",
            "Iniciar sesión con Microsoft (código de dispositivo)",
            self._start_login))
        card.body.addWidget(Divider())
        card.body.addWidget(section_label("Cuentas guardadas"))
        self.accounts_list = QListWidget()
        self.accounts_list.setMinimumHeight(88)
        self.accounts_list.setMaximumHeight(120)
        card.body.addWidget(self.accounts_list)

        self.accounts_empty = QLabel("Sin cuentas guardadas.")
        self.accounts_empty.setObjectName("emptyState")
        self.accounts_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.accounts_empty.setMinimumHeight(88)
        self.accounts_empty.setVisible(False)
        card.body.addWidget(self.accounts_empty)
        return card

    # ------------------------------------------------------------ offline
    def _on_offline_name(self, text: str) -> None:
        self.shell.settings.username = text.strip()
        error = validate_username(text.strip())
        if error:
            self.off_uuid.setText("UUID pendiente")
            self.off_uuid.setToolTip(error)
            self.off_avatar.set_identity(text or "?", text or "?")
        else:
            uuid_ = offline_uuid(text.strip())
            self.off_uuid.setText(f"UUID {uuid_}")
            self.off_uuid.setToolTip("UUID offline v3")
            self.off_avatar.set_identity(text.strip(), uuid_)
        self.shell._refresh_account()

    def _use_offline(self) -> None:
        self.shell.settings.active_account = ""
        self.shell._save_settings()
        self.refresh_accounts()
        self.shell._refresh_account()

    def _copy_offline_uuid(self) -> None:
        text = self.off_uuid.text().strip()
        if text.lower().startswith("uuid "):
            text = text[5:].strip()
        if text and "pendiente" not in text.lower():
            QApplication.clipboard().setText(text)
            self.shell._set_status("UUID copiado.", "ok")

    # --------------------------------------------------------- microsoft
    def _start_login(self) -> None:
        worker = self._login_worker
        if worker is not None and worker.isRunning():
            return
        dialog = MSLoginDialog(self)
        self._login_dialog = dialog
        worker = MSLoginWorker(self)
        worker.code_ready.connect(dialog.show_code)
        worker.done.connect(self._on_login_done)
        worker.failed.connect(self._on_login_failed)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(
            lambda: setattr(self, "_login_worker", None))
        self._login_worker = worker
        dialog.cancel_requested.connect(worker.cancel)
        dialog.finished.connect(lambda *_: worker.cancel())
        worker.start()
        dialog.exec()

    def _on_login_done(self, session: msauth.McSession,
                       refresh_token: str) -> None:
        database.save_account(session.uuid, session.name, refresh_token)
        self.shell.console.append(
            f"Cuenta Microsoft vinculada: {session.name} ({session.uuid})")
        self.refresh_accounts()
        if self._login_dialog:
            self._login_dialog.accept()

    def _on_login_failed(self, message: str) -> None:
        if self._login_dialog:
            self._login_dialog.show_error(message)

    def refresh_active_summary(self) -> None:
        name, uuid_, kind, online = self.shell._active_identity()
        self.active_avatar.set_identity(name or "?", uuid_ or name or "?")
        self.active_name.setText(name or "Sin perfil")
        self.active_uuid.setText(f"UUID {uuid_}" if uuid_
                                 else "UUID pendiente")
        self.active_pill.setText(kind)
        self.active_pill.set_dim(not online)

    def refresh_accounts(self) -> None:
        accounts = database.list_accounts()
        active = (self.shell.settings.active_account or "")
        connected = any(f"ms:{a['mc_uuid']}" == active for a in accounts)
        self.ms_status.setText("CONECTADA" if connected else "SIN SESIÓN")
        self.ms_status.set_dim(not connected)
        self.refresh_active_summary()
        self.accounts_list.clear()
        self.accounts_list.setVisible(bool(accounts))
        self.accounts_empty.setVisible(not accounts)
        if not accounts:
            return
        for account in accounts:
            key = f"ms:{account['mc_uuid']}"
            row, layout = list_row()
            info = QVBoxLayout()
            info.setContentsMargins(0, 0, 0, 0)
            info.setSpacing(1)
            name = QLabel(account["mc_name"])
            name.setObjectName("valueLabel")
            detail = QLabel(f"UUID {account['mc_uuid']}")
            detail.setObjectName("mono")
            detail.setWordWrap(True)
            info.addWidget(name)
            info.addWidget(detail)
            layout.addLayout(info, 1)

            if key == active:
                layout.addWidget(Pill("ACTIVA", accent=True))
            else:
                layout.addWidget(make_button(
                    "Usar", "primary", "Jugar con esta cuenta",
                    lambda k=key: self._use_account(k)))
            layout.addWidget(make_button(
                "Quitar", "danger", "Eliminar esta cuenta del equipo",
                lambda aid=account["mc_uuid"]: self._remove_account(aid)))

            row.ensurePolished()
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.accounts_list.addItem(item)
            self.accounts_list.setItemWidget(item, row)

    def _use_account(self, key: str) -> None:
        self.shell.settings.active_account = key
        self.shell._save_settings()
        self.refresh_accounts()
        self.shell._refresh_account()

    def _remove_account(self, mc_uuid: str) -> None:
        answer = QMessageBox.question(
            self, "Quitar cuenta",
            f"Se eliminará la cuenta {mc_uuid} de este equipo.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        database.delete_account(mc_uuid)
        if self.shell.settings.active_account == f"ms:{mc_uuid}":
            self.shell.settings.active_account = ""
            self.shell._save_settings()
        self.refresh_accounts()
        self.shell._refresh_account()


class TipsDialog(QDialog):
    """Consejos de rendimiento para el equipo del usuario."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Consejos de rendimiento")
        self.setWindowIcon(theme.app_icon())
        self.setModal(True)
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)

        title = QLabel("Consejos de rendimiento")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        body = QLabel(
            "• 2–4 GB de RAM suelen ser suficientes.\n"
            "• Serial en equipos modestos; G1 en potentes.\n"
            "• Cierra el launcher al jugar.\n"
            "• Mantén los drivers de la GPU al día.\n"
            "• En Fabric, Sodium y Lithium mejoran los FPS.")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(body)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(make_button(
            "Cerrar", "primary", "Cerrar este diálogo",
            self.accept))
        layout.addLayout(buttons)


class MSLoginDialog(QDialog):
    """Muestra el código de dispositivo mientras el worker espera."""

    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._device = None
        self.setWindowTitle("Iniciar sesión con Microsoft")
        self.setWindowIcon(theme.app_icon())
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

        title = QLabel("Iniciar sesión con Microsoft")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.status = QLabel("Solicitando código…")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.code_label = QLabel("")
        self.code_label.setObjectName("codeLabel")
        self.code_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.code_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.code_label)

        self.link_label = QLabel("")
        self.link_label.setObjectName("muted")
        self.link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.link_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.link_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        self.copy_button = make_button(
            "Copiar código", "accent",
            "Copia el código de dispositivo al portapapeles",
            self._copy_code)
        self.copy_button.setEnabled(False)
        self.open_button = make_button(
            "Abrir Microsoft", "primary",
            "Abrir la página oficial de inicio de sesión",
            self._open_link)
        buttons.addWidget(self.copy_button)
        buttons.addWidget(self.open_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.wait_label = muted_label("Esperando confirmación…")
        self.wait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wait_label)
        self.wait_label.setVisible(False)

        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(make_button(
            "Cancelar", "ghost", "Cancelar el inicio de sesión",
            self._cancel))
        layout.addLayout(footer)

    def show_code(self, device: msauth.DeviceCode) -> None:
        self._device = device
        self.code_label.setText(device.user_code)
        self.status.setObjectName("muted")
        repolish(self.status)
        self.status.setText("Código de verificación:")
        link = (f"<a href='{device.verification_uri}' "
                f"style='color:{theme.COLORS['ACCENT']}'>"
                f"{device.verification_uri}</a>")
        self.link_label.setText(link)
        self.link_label.setOpenExternalLinks(True)
        self.copy_button.setEnabled(True)
        self.progress.setVisible(True)
        self.wait_label.setVisible(True)

    def show_error(self, message: str) -> None:
        self.status.setText(message)
        self.status.setObjectName("statusError")
        repolish(self.status)
        self.code_label.setText("")
        self.link_label.setText("")
        self.copy_button.setEnabled(False)
        self.progress.setVisible(False)
        self.wait_label.setVisible(False)

    def _copy_code(self) -> None:
        if self._device and self._device.user_code:
            QApplication.clipboard().setText(self._device.user_code)
            self.status.setText("Código copiado.")

    def _open_link(self) -> None:
        if self._device and self._device.verification_uri:
            QDesktopServices.openUrl(QUrl(self._device.verification_uri))

    def _cancel(self) -> None:
        self.cancel_requested.emit()
        self.reject()


# =============================================================== AJUSTES
class SettingsPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._dirty = False
        self._loading = True
        self._build()
        self._loading = False
        self._connect_dirty_signals()
        self._refresh_dirty()

    def _build(self) -> None:
        header = PageHeader(
            "Ajustes", "Java, rendimiento, mods y datos del launcher.")
        self.dirty_pill = Pill("SIN GUARDAR")
        self.dirty_pill.setVisible(False)
        header.add_action(self.dirty_pill)
        self.header_save = make_button(
            "Guardar", "primary",
            "Guardar los ajustes de esta pantalla",
            self._save)
        header.add_action(self.header_save)
        self.body.addWidget(header)

        self.body.addWidget(self._appearance_card())
        self.body.addWidget(self._java_card())
        self.body.addWidget(self._performance_card())
        self.body.addWidget(self._mods_card())
        self.body.addWidget(self._data_card())

        self.body.addStretch(1)

    # ---------------------------------------------------------- apariencia
    def _appearance_card(self) -> Card:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(section_label("Apariencia"))
        row.addStretch(1)
        segmented = QFrame()
        segmented.setObjectName("segmented")
        segmented_layout = QHBoxLayout(segmented)
        segmented_layout.setContentsMargins(3, 3, 3, 3)
        segmented_layout.setSpacing(3)
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_buttons: dict[str, QPushButton] = {}
        for name, label in (("light", "☀   Claro"), ("dark", "☾   Oscuro")):
            button = make_button(
                label, "segment",
                f"Usar el tema {theme.THEME_NAMES.get(name, name).lower()}")
            button.setCheckable(True)
            button.clicked.connect(
                lambda _checked=False, value=name:
                self._on_theme_segment(value))
            self.theme_group.addButton(button)
            self.theme_buttons[name] = button
            segmented_layout.addWidget(button)
        row.addWidget(segmented, 0, Qt.AlignmentFlag.AlignVCenter)
        card.body.addLayout(row)
        self.refresh_theme_segment()
        return card

    def refresh_theme_segment(self) -> None:
        current = theme.current_theme_name()
        for name, button in getattr(self, "theme_buttons", {}).items():
            button.setChecked(name == current)

    def _on_theme_segment(self, name: str) -> None:
        self.shell._apply_ui_theme(name)
        self.refresh_theme_segment()

    # ---------------------------------------------------------------- java
    def _java_card(self) -> Card:
        settings = self.shell.settings
        card = Card()
        card.body.addWidget(section_label("Java y arranque"))

        form = QFormLayout()
        form.setSpacing(8)
        form.setHorizontalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        java_row = QWidget()
        java_layout = QHBoxLayout(java_row)
        java_layout.setContentsMargins(0, 0, 0, 0)
        java_layout.setSpacing(8)
        self.java_edit = QLineEdit(settings.java_path)
        self.java_edit.setPlaceholderText("Detección automática (javaw.exe)")
        java_layout.addWidget(self.java_edit, 1)
        java_layout.addWidget(make_button(
            "Examinar…", "ghost", "Seleccionar javaw.exe",
            self._browse_java))
        java_layout.addWidget(make_button(
            "Automática", "ghost",
            "Vaciar la ruta y dejar que el launcher detecte Java",
            self._clear_java_path))
        form.addRow("Ruta de Java", java_row)

        self.auto_java = QCheckBox(
            "Descargar Microsoft OpenJDK automáticamente si falta Java")
        self.auto_java.setChecked(settings.auto_download_java)
        form.addRow("", self.auto_java)

        self.jvm_edit = QLineEdit(settings.extra_jvm_args)
        self.jvm_edit.setPlaceholderText(
            "Ej: -XX:+UseG1GC -Dfile.encoding=UTF-8")
        self.jvm_edit.setToolTip(
            "Argumentos extra para la JVM. Sepáralos con espacios.")
        form.addRow("Argumentos JVM", self.jvm_edit)
        card.body.addLayout(form)

        detected = java_module.find_runtimes()
        if detected:
            summary = " · ".join(
                f"Java {item.major} ({item.source})" for item in detected[:4]
            )
        else:
            summary = "No se detectó Java instalado."
        card.body.addWidget(faint_label(f"Detectados: {summary}"))
        return card

    def _clear_java_path(self) -> None:
        self.java_edit.setText("")

    def _browse_java(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ejecutable de Java", "",
            "Ejecutable de Java (*.exe);;Todos los archivos (*)",
        )
        if selected:
            self.java_edit.setText(selected)

    # --------------------------------------------------------- rendimiento
    def _performance_card(self) -> Card:
        settings = self.shell.settings
        card = Card()
        card.body.addWidget(section_label("Rendimiento"))
        form = QFormLayout()
        form.setSpacing(8)
        form.setHorizontalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self.priority_combo = QComboBox()
        for value, label in (("idle", "Reposo"),
                             ("below_normal", "Baja"),
                             ("normal", "Normal"),
                             ("above_normal", "Alta"),
                             ("high", "Muy alta")):
            self.priority_combo.addItem(label, value)
        self.priority_combo.setToolTip(
            "Prioridad del proceso de Java. Baja/reposo reduce el impacto "
            "en el resto del sistema.")
        self.priority_combo.setMaximumWidth(380)
        index = self.priority_combo.findData(settings.game_priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        form.addRow("Prioridad del proceso", self.priority_combo)

        self.gc_combo = QComboBox()
        for value, label in (("auto", "Automático"),
                             ("g1", "G1GC"),
                             ("serial", "Serial"),
                             ("parallel", "Parallel")):
            self.gc_combo.addItem(label, value)
        self.gc_combo.setToolTip(
            "Recolector de basura de la JVM. Serial consume menos CPU y RAM "
            "en equipos modestos; G1 suele dar mejor rendimiento.")
        self.gc_combo.setMaximumWidth(380)
        index = self.gc_combo.findData(settings.gc_preset)
        if index >= 0:
            self.gc_combo.setCurrentIndex(index)
        form.addRow("Recolector (GC)", self.gc_combo)

        self.cores_spin = QSpinBox()
        max_cores = os.cpu_count() or 32
        self.cores_spin.setRange(0, max_cores)
        self.cores_spin.setSpecialValueText("Todos")
        self.cores_spin.setValue(max(0, min(max_cores, settings.cpu_cores)))
        self.cores_spin.setToolTip(
            "Limita el juego a N núcleos lógicos (0 = usar todos).")
        self.cores_spin.setFixedWidth(120)
        form.addRow("Núcleos de CPU", self.cores_spin)
        card.body.addLayout(form)

        optimize_row = QHBoxLayout()
        optimize_row.setSpacing(8)
        optimize_row.addWidget(make_button(
            "Optimizar para este equipo", "accent",
            "Detecta tu hardware y aplica RAM y GC recomendados",
            self._optimize_for_hardware))
        optimize_row.addStretch(1)
        card.body.addLayout(optimize_row)
        return card

    def _optimize_for_hardware(self) -> None:
        """Aplica ajustes recomendados según el hardware detectado.

        Equipo modesto (<=4 núcleos o <=6 GB RAM o sin AVX2): prioriza
        FPS — menos RAM asignada y GC Serial. Equipo potente: automático.
        """
        cores = hardware.cpu_cores()
        total_ram = hardware.ram_mb()
        flags = hardware.cpu_flags()
        modest = (cores <= 4 or total_ram <= 6144
                  or not flags.get("avx2")
                  or (hardware.has_integrated_gpu() and total_ram <= 8192))

        recommended = min(hardware.recommended_memory_mb(),
                          self.shell.play_page.ram_slider.maximum())
        recommended = max(self.shell.play_page.ram_slider.minimum(),
                          recommended)
        self.shell.play_page.ram_slider.setValue(recommended)

        gc_target = "serial" if modest else "auto"
        index = self.gc_combo.findData(gc_target)
        if index >= 0:
            self.gc_combo.setCurrentIndex(index)
        self.shell._save_settings()
        self._set_status_ok("Ajustes recomendados aplicados para este equipo.")

    def _set_status_ok(self, message: str) -> None:
        self.shell._set_status(message, "ok")

    # --------------------------------------------------------------- mods
    def _mods_card(self) -> Card:
        card = Card()
        card.body.addWidget(section_label("Mods"))
        self.mods_list = QListWidget()
        self.mods_list.setMinimumHeight(96)
        self.mods_list.setMaximumHeight(150)
        card.body.addWidget(self.mods_list)
        self.mods_loader_label = faint_label("")
        card.body.addWidget(self.mods_loader_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(make_button(
            "Añadir .jar…", "accent", "Instalar uno o varios mods",
            self._add_mod))
        row.addWidget(make_button(
            "Quitar", "danger", "Quitar el mod seleccionado",
            self._remove_mod))
        row.addWidget(make_button(
            "Abrir carpeta", "ghost", "Abrir la carpeta mods del juego",
            lambda: _open_path(mods.mods_dir())))
        row.addStretch(1)
        card.body.addLayout(row)

        loaders_row = QHBoxLayout()
        loaders_row.setSpacing(8)
        loaders_row.addWidget(faint_label("Loaders:"))
        for kind, label, tip in (
                ("forge", "Forge", "necesario para la mayoría de mods"),
                ("fabric", "Fabric", "loader ligero, mods de Fabric"),
                ("neoforge", "NeoForge", "continuación moderna de Forge")):
            loaders_row.addWidget(make_button(
                f"{label}…", "accent",
                f"Instala {label} ({tip}) para la versión seleccionada "
                "en Jugar, sin abrir ventanas.",
                lambda k=kind: self._install_loader(k)))
        loaders_row.addStretch(1)
        card.body.addLayout(loaders_row)
        self._refresh_mods()
        return card

    def _refresh_mods(self) -> None:
        self.mods_list.clear()
        installed = mods.list_mods()
        for mod in installed:
            label = mod.title if mod.title and mod.title != mod.name \
                else mod.name
            if mod.version:
                label += f" {mod.version}"
            badge = f" · {mod.loader.capitalize()}" if mod.loader else ""
            item = QListWidgetItem(
                f"{label}{badge}  ·  {human_size(mod.size)}")
            item.setData(Qt.ItemDataRole.UserRole, mod.name)
            deps = mod.depends or {}
            hints = [f"requiere {key} {value}"
                     for key, value in sorted(deps.items())
                     if key in ("minecraft", "java", "loader")]
            item.setToolTip("\n".join([mod.name, *hints])
                            if hints else mod.name)
            self.mods_list.addItem(item)
        if not installed:
            empty = QListWidgetItem("No hay mods instalados.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.mods_list.addItem(empty)
        grouped = loaders.installed_loader_profiles()
        parts = []
        for kind in ("forge", "fabric", "neoforge", "optifine"):
            ids = grouped.get(kind) or []
            if ids:
                shown = ", ".join(ids[:2])
                extra = f" (+{len(ids) - 2})" if len(ids) > 2 else ""
                parts.append(f"{kind.capitalize()} {shown}{extra}")
        self.mods_loader_label.setText(
            " · ".join(parts) if parts else "Sin loaders")

    def showEvent(self, event) -> None:  # noqa: N802 - API de Qt
        super().showEvent(event)
        self._refresh_mods()
        self.refresh_theme_segment()

    def _add_mod(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Añadir mod (.jar)", "",
            "Mods de Minecraft (*.jar);;Todos los archivos (*)")
        if not selected:
            return
        try:
            info = mods.install_mod(Path(selected))
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            QMessageBox.warning(self, "No se pudo instalar el mod",
                                str(error))
            return
        self._refresh_mods()
        self.shell._set_status(f"Mod instalado: {info.name}", "ok")
        self._maybe_offer_loader(Path(selected), info.loader)

    _LOADER_NAMES = {"forge": "Forge", "fabric": "Fabric",
                     "neoforge": "NeoForge"}

    def _maybe_offer_loader(self, jar: Path, kind: str) -> None:
        """Ofrece instalar el loader que necesita el mod, si falta."""
        if not kind or kind == "optifine":
            return
        if loaders.has_loader_profile(kind):
            return
        base = self.shell._selected_base() or self.shell._selected_version()
        if not base:
            return
        name = self._LOADER_NAMES.get(kind, kind)
        answer = QMessageBox.question(
            self, f"Mod de {name} detectado",
            f"'{jar.name}' es un mod de {name}. {name} no está instalado.\n\n"
            f"¿Instalar {name} para Minecraft {base} ahora?\n"
            "Se descargará e instalará automáticamente.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer == QMessageBox.StandardButton.Yes:
            self._install_loader(kind)

    def _remove_mod(self) -> None:
        item = self.mods_list.currentItem()
        if not item:
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        if not name:
            return
        try:
            mods.remove_mod(name)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo quitar el mod", str(error))
            return
        self._refresh_mods()
        self.shell._set_status(f"Mod eliminado: {name}", "ok")

    def _install_loader(self, kind: str) -> None:
        version_id = self.shell._selected_base() or ""
        if not version_id:
            name = self._LOADER_NAMES.get(kind, kind)
            QMessageBox.information(
                self, name, "Selecciona una versión en Jugar.")
            return
        self._loader_base = version_id
        self._loader_kind = kind
        if kind == "forge":
            worker = ForgeInstallWorker(version_id, self.shell.settings,
                                        self)
        else:
            worker = LoaderInstallWorker(kind, version_id,
                                         self.shell.settings, self)
        worker.stage.connect(
            lambda text: self.shell.stage_label.setText(text))
        worker.progress.connect(self.shell._set_progress)
        worker.log.connect(lambda text: self.shell.console.append(text))
        worker.cancelled.connect(
            lambda: self.shell._set_status(
                f"Instalación de {kind} cancelada.", "error"))
        worker.done.connect(lambda name: self._loader_done(name))
        worker.failed.connect(
            lambda msg: QMessageBox.warning(
                self, self._LOADER_NAMES.get(kind, kind), msg))
        worker.finished.connect(worker.deleteLater)
        self._loader_worker = worker
        worker.start()

    def _loader_done(self, profile: str) -> None:
        base = getattr(self, "_loader_base", "") or \
            self.shell._selected_base()
        kind = getattr(self, "_loader_kind", "")
        name = self._LOADER_NAMES.get(kind, kind.capitalize())
        found = None
        if base:
            if kind == "forge":
                found = forge._find_forge_profile(base)
            else:
                found = loaders.find_loader_profile(kind, base)
        if found:
            # El worker emite la version del loader, no el id del perfil:
            # solo se celebra exito cuando el perfil existe de verdad.
            self.shell._set_status(
                f"{name} instalado: perfil '{found}'.", "ok")
            self.shell._reload_versions()
            self._refresh_mods()
            return
        # Respaldo con instalador gráfico: vigilar la aparición del perfil.
        self.shell._set_status(
            f"Instalador de {name} abierto — se detectará al terminar.",
            "ok")
        self._watch_loader(base, kind, 60)

    def _watch_loader(self, base: str, kind: str, attempts: int) -> None:
        if not base or attempts <= 0:
            return
        found = (forge._find_forge_profile(base) if kind == "forge"
                 else loaders.find_loader_profile(kind, base))
        if found:
            self.shell._set_status(
                f"Perfil de {self._LOADER_NAMES.get(kind, kind)} "
                "detectado.", "ok")
            self.shell._reload_versions()
            self._refresh_mods()
            return
        QTimer.singleShot(
            3000, lambda: self._watch_loader(base, kind, attempts - 1))

    # --------------------------------------------------------------- datos
    def _data_card(self) -> Card:
        settings = self.shell.settings
        card = Card()
        card.body.addWidget(section_label("Datos y configuración"))

        self.show_all = QCheckBox("Mostrar todas las versiones")
        self.show_all.setChecked(settings.show_all_versions)
        self.show_all.setToolTip(
            "Incluye las versiones antiguas y los snapshots en la lista de "
            "Jugar. Se admiten versiones desde Minecraft 1.7.")
        card.body.addWidget(self.show_all)

        self.offline_mode = QCheckBox("Modo sin conexión")
        self.offline_mode.setChecked(settings.offline_mode)
        self.offline_mode.setToolTip(
            "Juega solo con los archivos ya descargados: no consulta el "
            "manifiesto ni verifica SHA-1/SHA-256, y tolera descargas o "
            "índices que no estén en caché. Es útil sin conexión a Internet "
            "o con una conexión inestable.")
        card.body.addWidget(self.offline_mode)
        card.body.addWidget(Divider())

        self.data_grid = InfoGrid([
            ("Datos", str(paths.DATA_DIR)),
            (".minecraft", str(paths.MC_DIR)),
        ], key_width=88)
        card.body.addWidget(self.data_grid)
        extra = [line.strip()
                 for line in settings.extra_mc_dirs.splitlines()
                 if line.strip()]
        self.extra_dirs_label = faint_label(
            ".minecraft adicionales: " + " · ".join(extra) if extra else "")
        card.body.addWidget(self.extra_dirs_label)
        card.body.addWidget(Divider())

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(make_button(
            "Abrir datos", "ghost",
            "Abrir la carpeta con los ajustes, la caché y los registros",
            lambda: _open_path(paths.DATA_DIR)))
        actions.addWidget(make_button(
            "Limpiar caché", "ghost",
            "Borrar manifiestos y descargas temporales",
            self._clear_cache))
        actions.addWidget(make_button(
            "Exportar", "ghost",
            "Guardar una copia de settings.json",
            self._export_settings))
        actions.addWidget(make_button(
            "Importar", "ghost",
            "Restaurar una configuración exportada",
            self._import_settings))
        actions.addStretch(1)
        card.body.addLayout(actions)

        danger_row = QHBoxLayout()
        danger_row.setSpacing(8)
        danger_row.addWidget(make_button(
            "Vaciar datos", "danger",
            "Borra caché, Java y registros; conserva ajustes y .minecraft",
            self._wipe_data))
        danger_row.addWidget(make_button(
            "Restablecer", "danger",
            "Volver a los ajustes de fábrica",
            self._reset_settings))
        danger_row.addStretch(1)
        card.body.addLayout(danger_row)
        return card

    def _clear_cache(self) -> None:
        """Elimina el contenido de CACHE_DIR (seguro: se regenera solo)."""
        cache = paths.CACHE_DIR
        if not cache.exists():
            self.shell._set_status("La caché ya está vacía.", "ok")
            return
        answer = QMessageBox.question(
            self, "Limpiar caché",
            f"Se borrará el contenido de:\n{cache}\n\n"
            "Las versiones y mundos instalados no se ven afectados.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        freed = 0
        try:
            for item in cache.iterdir():
                if item.is_dir():
                    size = sum(f.stat().st_size for f in item.rglob("*")
                               if f.is_file())
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    size = item.stat().st_size
                    item.unlink(missing_ok=True)
                freed += size
        except OSError as error:
            self.shell._set_status(
                f"No se pudo limpiar la caché: {error}", "error")
            return
        cache.mkdir(parents=True, exist_ok=True)
        self.shell._set_status(
            f"Caché limpiada ({human_size(freed)} liberados).", "ok")

    def _wipe_data(self) -> None:
        """Vacía los datos del launcher sin tocar los ajustes ni .minecraft.

        Se conservan settings.json y todo el contenido de .minecraft,
        incluidas las versiones, los mundos y los mods. Java tendrá que
        descargarse de nuevo si hace falta.
        """
        data_dir = paths.DATA_DIR
        if not data_dir.exists():
            self.shell._set_status("No hay datos que borrar.", "ok")
            return
        items = [item for item in data_dir.iterdir()
                 if item.name != paths.SETTINGS_FILE.name]
        if not items:
            self.shell._set_status("Las carpetas de datos ya están vacías.",
                                   "ok")
            return
        names = ", ".join(sorted(item.name for item in items))
        answer = QMessageBox.question(
            self, "Vaciar datos",
            f"Se borrará TODO el contenido de:\n{data_dir}\n\n"
            f"Carpetas/archivos afectados: {names}\n\n"
            "Se conservan los ajustes (settings.json) y todo el contenido "
            "de .minecraft, incluidas las versiones, los mundos y los mods. "
            "Java tendrá que descargarse de nuevo si hace falta. "
            "¿Quieres continuar?", 
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        freed = 0
        errors = 0
        for item in items:
            try:
                if item.is_dir():
                    freed += sum(f.stat().st_size for f in item.rglob("*")
                                 if f.is_file())
                    shutil.rmtree(item)
                else:
                    freed += item.stat().st_size
                    item.unlink()
            except OSError:
                errors += 1
        data_dir.mkdir(parents=True, exist_ok=True)
        paths.ensure_dirs()
        if errors:
            self.shell._set_status(
                f"Datos borrados con {errors} errores "
                f"({human_size(freed)} liberados).", "error")
        else:
            self.shell._set_status(
                f"Datos borrados ({human_size(freed)} liberados).", "ok")

    def _export_settings(self) -> None:
        """Exporta settings.json a una ubicación elegida por el usuario."""
        source = paths.SETTINGS_FILE
        target, _ = QFileDialog.getSaveFileName(
            self, "Exportar ajustes", "azero-settings.json",
            "Configuración JSON (*.json)")
        if not target:
            return
        try:
            shutil.copy2(source, target)
        except OSError as error:
            self.shell._set_status(f"No se pudo exportar: {error}", "error")
            return
        self.shell._set_status(f"Ajustes exportados a {target}", "ok")

    def _import_settings(self) -> None:
        """Restaura un settings.json exportado previamente."""
        source, _ = QFileDialog.getOpenFileName(
            self, "Importar ajustes", "",
            "Configuración JSON (*.json)")
        if not source:
            return
        try:
            raw = json.loads(Path(source).read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("formato inválido")
        except (OSError, ValueError) as error:
            self.shell._set_status(
                f"Archivo de ajustes inválido: {error}", "error")
            return
        try:
            shutil.copy2(source, paths.SETTINGS_FILE)
        except OSError as error:
            self.shell._set_status(f"No se pudo importar: {error}", "error")
            return
        self.shell._set_status(
            "Ajustes importados. Reinicia el launcher para aplicarlos.", "ok")

    def _reset_settings(self) -> None:
        """Restablece settings.json a los valores por defecto."""
        answer = QMessageBox.question(
            self, "Restablecer ajustes",
            "Se borrará toda la configuración actual y se volverá a los "
            "valores de fábrica.\n\n¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            paths.SETTINGS_FILE.unlink(missing_ok=True)
        except OSError as error:
            self.shell._set_status(f"No se pudo restablecer: {error}", "error")
            return
        self.shell._set_status(
            "Ajustes restablecidos. Reinicia el launcher para aplicarlos.",
            "ok")

    # ------------------------------------------------------------ guardado
    def _connect_dirty_signals(self) -> None:
        self.java_edit.textChanged.connect(self._mark_dirty)
        self.auto_java.toggled.connect(self._mark_dirty)
        self.jvm_edit.textChanged.connect(self._mark_dirty)
        self.show_all.toggled.connect(self._mark_dirty)
        self.offline_mode.toggled.connect(self._mark_dirty)
        self.priority_combo.currentIndexChanged.connect(self._mark_dirty)
        self.gc_combo.currentIndexChanged.connect(self._mark_dirty)
        self.cores_spin.valueChanged.connect(self._mark_dirty)

    def _mark_dirty(self, *_args) -> None:
        if self._loading:
            return
        self._dirty = True
        self._refresh_dirty()

    def _refresh_dirty(self) -> None:
        dirty = self._dirty
        self.dirty_pill.setVisible(dirty)
        self.header_save.setEnabled(dirty)

    def save_if_dirty(self) -> None:
        """Guarda sin avisos al cerrar el launcher."""
        if self._dirty:
            self._save(silent=True)

    def _save(self, silent: bool = False) -> None:
        settings = self.shell.settings
        settings.java_path = self.java_edit.text().strip()
        settings.auto_download_java = self.auto_java.isChecked()
        settings.extra_jvm_args = self.jvm_edit.text().strip()
        reload_needed = (
            self.show_all.isChecked() != settings.show_all_versions
            or self.offline_mode.isChecked() != settings.offline_mode)
        settings.show_all_versions = self.show_all.isChecked()
        settings.offline_mode = self.offline_mode.isChecked()
        settings.game_priority = (
            self.priority_combo.currentData() or "normal")
        settings.gc_preset = self.gc_combo.currentData() or "auto"
        settings.cpu_cores = self.cores_spin.value()
        self.shell._save_settings()
        if reload_needed and not silent:
            self.shell._reload_versions()
        self._dirty = False
        self._refresh_dirty()
        if not silent:
            self.shell.console.append("Ajustes guardados.")
            self.shell._set_status("Ajustes guardados.", "ok")


# ============================================================= ACERCA DE
def _version_key(text: str) -> tuple[int, ...]:
    """Convierte 'v1.2.3' en una tupla comparable de versiones."""
    parts = re.findall(r"\d+", text or "")
    return tuple(int(part) for part in parts[:3])


class _UpdateChecker(QThread):
    """Consulta el último release de GitHub sin bloquear la UI."""

    checked = pyqtSignal(str, str, str)   # tag, release, instalador

    def run(self) -> None:
        import urllib.request
        try:
            request = urllib.request.Request(
                LATEST_RELEASE_API,
                headers={"User-Agent": USER_AGENT,
                         "Accept": "application/vnd.github+json"})
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))
            tag = str(data.get("tag_name", ""))
            page_url = str(data.get("html_url", "")) or RELEASES_URL
            asset_url = ""
            for asset in data.get("assets") or []:
                name = str(asset.get("name", "")).lower()
                url = str(asset.get("browser_download_url", ""))
                if url and name.endswith(".exe") and "setup" in name:
                    asset_url = url
                    break
            self.checked.emit(tag, page_url, asset_url)
        except Exception:  # noqa: BLE001 - sin red o repo sin releases
            self.checked.emit("", "", "")


class AboutPage(ScrollPage):
    """Pantalla 'Acerca de': información, enlaces, soporte y diagnóstico."""

    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._update_started = False
        self._build()

    # ------------------------------------------------------------- build
    def _build(self) -> None:
        self.body.addWidget(self._hero_card())
        self._project_card()
        self._support_card()
        self._system_card()
        self.body.addStretch(1)

    def _hero_card(self) -> Card:
        card = Card()
        row = QHBoxLayout()
        row.setSpacing(14)
        icon = QLabel()
        icon.setPixmap(theme.app_icon().pixmap(48, 48))
        icon.setFixedSize(48, 48)
        row.addWidget(icon)
        column = QVBoxLayout()
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        name = QLabel(f"{APP_NAME} Launcher")
        name.setObjectName("appTitle")
        column.addWidget(name)
        meta = QLabel(
            f"v{APP_VERSION} · Launcher de Minecraft Java Edition")
        meta.setObjectName("muted")
        meta.setWordWrap(True)
        column.addWidget(meta)
        row.addLayout(column, 1)

        updates = QVBoxLayout()
        updates.setSpacing(4)
        head = QHBoxLayout()
        head.setSpacing(6)
        self.update_pill = Pill("SIN COMPROBAR", dim=True)
        head.addWidget(self.update_pill)
        self.update_check_button = make_button(
            "Comprobar", "ghost",
            "Buscar una versión nueva en GitHub",
            self._start_update_check)
        head.addWidget(self.update_check_button)
        updates.addLayout(head)
        self.update_label = QLabel("")
        self.update_label.setObjectName("muted")
        updates.addWidget(self.update_label)
        row.addLayout(updates, 0)
        card.body.addLayout(row)

        self.update_page_url = RELEASES_URL
        self.update_asset_url = ""
        self.update_button = make_button(
            "Descargar instalador", "accent",
            "Abrir la descarga del instalador",
            self._open_update_download)
        self.update_button.setVisible(False)
        self.update_notes_button = make_button(
            "Ver notas", "ghost",
            "Abrir la página del release",
            self._open_update_page)
        self.update_notes_button.setVisible(False)
        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(self.update_button)
        actions.addWidget(self.update_notes_button)
        actions.addStretch(1)
        card.body.addLayout(actions)
        return card

    def _project_card(self) -> None:
        card = Card()
        card.body.addWidget(section_label("Proyecto"))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(link_button("GitHub", REPO_URL))
        row.addWidget(link_button("Releases", RELEASES_URL))
        row.addWidget(link_button("Issues", ISSUES_URL))
        row.addWidget(link_button("Documentación", DOCS_URL))
        row.addStretch(1)
        card.body.addLayout(row)
        card.body.addWidget(faint_label(
            "Código abierto · no afiliado a Mojang."))
        self.body.addWidget(card)

    def _support_card(self) -> None:
        card = Card()
        card.body.addWidget(section_label("Apoya el proyecto"))
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(link_button(
            "Donar", SPONSORS_URL, "primary",
            "Abrir la página de patrocinio"))
        row.addWidget(make_button(
            "Copiar diagnóstico", "ghost",
            "Copia la información del sistema para reportar un problema",
            self._copy_diagnostics))
        row.addStretch(1)
        card.body.addLayout(row)
        card.body.addWidget(faint_label("Donaciones voluntarias."))
        self.body.addWidget(card)

    def ensure_update_check(self) -> None:
        """Inicia la comprobación de versión al abrir la página."""
        if self._update_started:
            return
        self._start_update_check()

    def _start_update_check(self) -> None:
        checker = getattr(self, "_update_checker", None)
        if checker is not None and checker.isRunning():
            return
        self._update_started = True
        self.update_pill.setText("COMPROBANDO")
        self.update_pill.set_dim(True)
        self.update_label.setText("")
        self.update_check_button.setEnabled(False)
        self.update_button.setVisible(False)
        self.update_notes_button.setVisible(False)
        checker = _UpdateChecker(self)
        checker.checked.connect(self._on_update_checked)
        checker.finished.connect(self._on_update_finished)
        self._update_checker = checker
        checker.start()

    def _on_update_finished(self) -> None:
        checker = getattr(self, "_update_checker", None)
        self._update_checker = None
        if checker is not None:
            checker.deleteLater()

    def _on_update_checked(self, tag: str, page_url: str,
                           asset_url: str) -> None:
        self.update_check_button.setEnabled(True)
        self.update_page_url = page_url or RELEASES_URL
        self.update_asset_url = asset_url
        if not tag:
            self.update_pill.setText("SIN CONEXIÓN")
            self.update_pill.set_dim(True)
            self.update_label.setText("Sin conexión.")
            self.update_button.setVisible(False)
            self.update_notes_button.setVisible(False)
            return
        if _version_key(tag) <= _version_key(APP_VERSION):
            self.update_pill.setText("AL DÍA")
            self.update_pill.set_dim(False)
            self.update_label.setText("")
            self.update_button.setVisible(False)
            self.update_notes_button.setVisible(False)
            return
        self.update_pill.setText("NUEVA VERSIÓN")
        self.update_pill.set_dim(False)
        self.update_label.setText(f"Disponible {tag}")
        self.update_button.setText(
            "Descargar instalador" if asset_url else "Ver releases")
        self.update_button.setVisible(True)
        self.update_notes_button.setVisible(True)

    def _open_update_download(self) -> None:
        url = self.update_asset_url or self.update_page_url
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def _open_update_page(self) -> None:
        if self.update_page_url:
            QDesktopServices.openUrl(QUrl(self.update_page_url))

    def _system_card(self) -> None:
        card = Card()
        card.body.addWidget(section_label("Sistema"))
        gpu = hardware.gpu_name()
        rows = [
            ("Hardware", hardware.summary()),
            ("GPU", gpu or "No detectada"),
            ("RAM sugerida", f"{hardware.recommended_memory_mb()} MB para MC"),
            ("Carpeta de datos", str(paths.DATA_DIR)),
            ("Python", f"{sys.version_info.major}."
                       f"{sys.version_info.minor}."
                       f"{sys.version_info.micro}"),
            ("Plataforma", f"{sys.platform} · {platform.machine()}"),
        ]
        card.body.addWidget(InfoGrid(rows, key_width=132))
        legal_row = QHBoxLayout()
        legal_row.setSpacing(8)
        legal_row.addWidget(faint_label(
            "No redistribuye archivos de Minecraft. Sin garantías."))
        legal_row.addStretch(1)
        legal_row.addWidget(link_button(
            "Licencia",
            f"{REPO_URL}/blob/main/installer/license.txt"))
        card.body.addLayout(legal_row)
        self.body.addWidget(card)

    # ------------------------------------------------------------ helpers
    def _copy_diagnostics(self) -> None:
        """Copia un informe del sistema al portapapeles."""
        settings = self.shell.settings
        lines = [
            f"{APP_NAME} {APP_VERSION}",
            f"Repo: {REPO_URL}",
            f"GPU: {hardware.gpu_name() or 'no detectada'}",
            f"Hardware: {hardware.summary()}",
            f"RAM sugerida: {hardware.recommended_memory_mb()} MB",
            f"Flags CPU: {hardware.supported_flags_text()}",
            f"Datos: {paths.DATA_DIR}",
            f"Java path: {settings.java_path or 'automático'}",
            f"Versión MC: {settings.version}",
            f"RAM asignada: {settings.memory_mb} MB",
            f"Plataforma: {sys.platform} {platform.machine()} "
            f"Python {sys.version_info.major}.{sys.version_info.minor}.",
        ]
        QApplication.clipboard().setText("\n".join(lines))
        self.shell._set_status(
            "Diagnóstico copiado al portapapeles.", "ok")
