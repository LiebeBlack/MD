"""Paginas de la interfaz: Jugar, Versiones, Cuenta y Ajustes."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main_window import MainWindow

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog,
                             QFormLayout, QFrame, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem,
                             QMessageBox, QProgressBar, QPushButton,
                             QScrollArea, QSpinBox,
                             QSlider, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

from .. import (APP_NAME, APP_VERSION, database, hardware,
                java as java_module, msauth, paths)
from ..auth import offline_uuid, validate_username
from ..constants import MEMORY_STEP_MB, MIN_MEMORY_MB
from ..manifest import parse_version_key
from ..util import human_size
from ..workers import MSLoginWorker
from . import theme
from .widgets import (Avatar, Card, ConsoleView, Divider, Pill, faint_label,
                      muted_label, section_label)


def _gb_text(memory_mb: int) -> str:
    value = memory_mb / 1024
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text} GB"


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


class ScrollPage(QWidget):
    """Pagina con scroll vertical para que nada se corte en ventanas
    pequenas (evita errores de visualizacion por desbordamiento)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("page")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content = QWidget()
        self.content.setObjectName("page")
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(18, 14, 18, 14)
        self.body.setSpacing(12)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)


# ================================================================ JUGAR
class PlayPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._build()

    # ------------------------------------------------------------- build
    def _build(self) -> None:
        head = QHBoxLayout()
        head.setSpacing(8)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("Jugar")
        title.setObjectName("pageTitle")
        sub = QLabel("Elige tu jugador y version, y pulsa JUGAR.")
        sub.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch(1)
        self.head_pill = Pill("Modo offline")
        head.addWidget(self.head_pill)
        self.body.addLayout(head)

        columns = QHBoxLayout()
        columns.setSpacing(14)

        left = QWidget()
        left.setFixedWidth(384)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_layout.addWidget(self._account_card())
        left_layout.addWidget(self._version_card())
        left_layout.addWidget(self._quick_card())

        self.play_button = QPushButton("JUGAR")
        self.play_button.setObjectName("playButton")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setMinimumHeight(46)
        self.play_button.clicked.connect(self.shell._on_play_clicked)
        left_layout.addWidget(self.play_button)

        self.stage_label = muted_label("Esperando accion.")
        self.stage_label.setWordWrap(True)
        left_layout.addWidget(self.stage_label)
        left_layout.addStretch(1)
        columns.addWidget(left)

        console_card = Card(margins=12, spacing=8)
        console_head = QHBoxLayout()
        console_head.addWidget(section_label("Registro"))
        console_head.addStretch(1)
        open_folder = QPushButton("Carpeta")
        open_folder.setObjectName("ghostButton")
        open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder.clicked.connect(self.shell._open_mc_folder)
        clear = QPushButton("Limpiar")
        clear.setObjectName("ghostButton")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(lambda: self.console.clear())
        console_head.addWidget(open_folder)
        console_head.addWidget(clear)
        console_card.body.addLayout(console_head)

        self.console = ConsoleView()
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
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.percent_label)
        console_card.body.addLayout(progress_row)

        columns.addWidget(console_card, 1)
        self.body.addLayout(columns, 1)

    def _account_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Jugador"))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.avatar = Avatar(54)
        column = QVBoxLayout()
        column.setSpacing(3)

        self.name_edit = QLineEdit(self.shell.settings.username)
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setMaxLength(16)
        self.name_edit.setPlaceholderText("Nombre de jugador")
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
        card.body.addLayout(row)

        footer = QHBoxLayout()
        self.mode_pill = Pill("SIN CUENTAS", dim=True)
        footer.addWidget(self.mode_pill)
        footer.addStretch(1)
        footer.addWidget(faint_label("Cambiar en la pestana Cuenta"))
        card.body.addLayout(footer)
        return card

    def _version_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Version"))

        self.version_combo = QComboBox()
        self.version_combo.setPlaceholderText("Cargando versiones…")
        self.version_combo.currentIndexChanged.connect(
            self.shell._on_version_changed)
        card.body.addWidget(self.version_combo)

        self.version_meta = muted_label("Leyendo el manifiesto oficial de Mojang…")
        self.version_meta.setWordWrap(True)
        card.body.addWidget(self.version_meta)
        card.body.addWidget(Divider())

        row = QHBoxLayout()
        row.setSpacing(10)
        column = QVBoxLayout()
        column.setSpacing(2)
        title = QLabel("OptiFine")
        title.setObjectName("valueLabel")
        self.optifine_status = faint_label("Comprobando estado…")
        self.optifine_status.setWordWrap(True)
        column.addWidget(title)
        column.addWidget(self.optifine_status)
        self.optifine_button = QPushButton("Instalar…")
        self.optifine_button.setObjectName("accentGhost")
        self.optifine_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.optifine_button.clicked.connect(self.shell._on_install_optifine)
        row.addLayout(column, 1)
        row.addWidget(self.optifine_button)
        card.body.addLayout(row)
        return card

    def _quick_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Ajustes rapidos"))

        head = QHBoxLayout()
        head.addWidget(section_label("Memoria RAM"))
        head.addStretch(1)
        self.ram_value = QLabel(_gb_text(self.shell.settings.memory_mb))
        self.ram_value.setObjectName("valueLabel")
        head.addWidget(self.ram_value)
        card.body.addLayout(head)

        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        ram_max = hardware.memory_slider_max_mb()
        self.ram_slider.setMinimum(MIN_MEMORY_MB)
        self.ram_slider.setMaximum(ram_max)
        self.ram_slider.setSingleStep(MEMORY_STEP_MB)
        self.ram_slider.setPageStep(1024)
        self.ram_slider.setToolTip(
            f"Maximo para tu equipo (~{_gb_text(ram_max)}): asignar mas RAM "
            "de la disponible provoca cierres y lentitud en el sistema."
        )
        self.ram_slider.valueChanged.connect(self.shell._on_ram_changed)
        self.ram_slider.sliderReleased.connect(self.shell._save_settings)
        card.body.addWidget(self.ram_slider)
        card.body.addWidget(faint_label(
            f"Detectado: {hardware.summary()} · max {_gb_text(ram_max)}"))

        self.server_edit = QLineEdit(self.shell.settings.server)
        self.server_edit.setPlaceholderText("Servidor opcional: play.ejemplo.net:25565")
        self.server_edit.editingFinished.connect(self.shell._on_server_changed)
        card.body.addWidget(self.server_edit)

        self.auto_close_check = QCheckBox("Cerrar el launcher al iniciar el juego")
        self.auto_close_check.setChecked(self.shell.settings.auto_close)
        self.auto_close_check.setToolTip(
            "El juego se ejecuta en un proceso independiente, por lo que el "
            "launcher puede cerrarse y liberar toda su memoria."
        )
        self.auto_close_check.toggled.connect(self.shell._on_auto_close_changed)
        card.body.addWidget(self.auto_close_check)
        return card

    # ------------------------------------------------------------ estado
    def refresh_account(self, name: str, uuid_: str, kind: str,
                        online: bool) -> None:
        self.avatar.set_identity(name or "?", uuid_ or name or "?")
        self.uuid_label.setText(f"UUID {uuid_}" if uuid_ else "UUID pendiente")
        self.head_pill.setText(kind.upper())
        self.mode_pill.setText("CUENTA MICROSOFT" if online else "OFFLINE")
        self.name_edit.setVisible(not online)
        self.account_label.setVisible(online)
        if online:
            self.account_label.setText(name)
        self.uuid_label.setToolTip(
            "Cuenta oficial de Minecraft" if online
            else "UUID offline v3 (Java nameUUIDFromBytes)"
        )

    def set_busy_widgets(self, busy: bool) -> None:
        for widget in (self.name_edit, self.version_combo, self.ram_slider,
                       self.auto_close_check, self.server_edit,
                       self.optifine_button):
            widget.setEnabled(not busy)


# ============================================================= VERSIONES
class VersionsPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._build()

    def _build(self) -> None:
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Versiones y archivos")
        title.setObjectName("pageTitle")
        sub = QLabel("Versiones instaladas, historial de descargas y registros.")
        sub.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch(1)
        clear = QPushButton("Limpiar historial")
        clear.setObjectName("dangerButton")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(self.clear_history)
        head.addWidget(clear)
        refresh = QPushButton("Actualizar")
        refresh.setObjectName("ghostButton")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.clicked.connect(self.refresh_all)
        head.addWidget(refresh)
        self.body.addLayout(head)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_versions = self._stat_card("VERSIONES", "0")
        self.stat_size = self._stat_card("TAMANO", "0 MB")
        self.stat_sessions = self._stat_card("PARTIDAS", "0")
        stats.addWidget(self.stat_versions)
        stats.addWidget(self.stat_size)
        stats.addWidget(self.stat_sessions)
        self.body.addLayout(stats)

        self.body.addWidget(section_label("Versiones instaladas"))
        self.installed_list = QListWidget()
        self.installed_list.setMinimumHeight(160)
        self.installed_list.setMaximumHeight(230)
        self.body.addWidget(self.installed_list)

        row = QHBoxLayout()
        row.addWidget(faint_label("Las librerias y assets se comparten entre "
                                  "versiones; el tamano mostrado es del cliente."))
        row.addStretch(1)
        open_mc = QPushButton("Abrir carpeta .minecraft")
        open_mc.setObjectName("ghostButton")
        open_mc.setCursor(Qt.CursorShape.PointingHandCursor)
        open_mc.clicked.connect(lambda: _open_path(paths.MC_DIR))
        row.addWidget(open_mc)
        self.body.addLayout(row)

        self.body.addWidget(Divider())
        self.body.addWidget(section_label("Historial de descargas"))
        self.downloads_table = self._make_table(
            ["Fecha", "Tipo", "Detalle", "Version", "Tamano", "Estado"])
        self.body.addWidget(self.downloads_table)

        self.body.addWidget(Divider())
        self.body.addWidget(section_label("Sesiones recientes"))
        self.sessions_table = self._make_table(
            ["Inicio", "Jugador", "Version", "Cuenta", "Duracion", "Estado"])
        self.body.addWidget(self.sessions_table)

        self.body.addWidget(Divider())
        self.body.addWidget(section_label("Registros del juego"))
        self.logs_list = QListWidget()
        self.logs_list.setMinimumHeight(110)
        self.logs_list.setMaximumHeight(180)
        self.logs_list.itemDoubleClicked.connect(self._open_log)
        self.body.addWidget(self.logs_list)
        self.body.addWidget(faint_label(
            "Doble clic en un registro para abrirlo."))

        self.body.addStretch(1)

    def _stat_card(self, caption: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName("statCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        val = QLabel(value)
        val.setObjectName("statValue")
        val.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        cap = QLabel(caption)
        cap.setObjectName("statCaption")
        cap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(val)
        layout.addWidget(cap)
        frame._value_label = val  # type: ignore[attr-defined]
        return frame

    def _make_table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setShowGrid(False)
        for column in range(len(headers) - 1):
            table.horizontalHeader().setSectionResizeMode(
                column, table.horizontalHeader()
                .ResizeMode.ResizeToContents)
        return table

    # ------------------------------------------------------------ datos
    def refresh_all(self) -> None:
        self._refresh_stats()
        self._refresh_installed()
        self._refresh_downloads()
        self._refresh_sessions()
        self._refresh_logs()

    def _refresh_stats(self) -> None:
        installed = self._scan_installed()
        total = sum(item["size"] for item in installed)
        self.stat_versions._value_label.setText(str(len(installed)))  # type: ignore[attr-defined]
        self.stat_size._value_label.setText(human_size(total))  # type: ignore[attr-defined]
        sessions = database.list_sessions(limit=500)
        played = sum(1 for s in sessions if s.get("ended"))
        self.stat_sessions._value_label.setText(str(played))  # type: ignore[attr-defined]

    def _scan_installed(self) -> list[dict]:
        entries = []
        if not paths.VERSIONS_DIR.exists():
            return entries
        for child in sorted(paths.VERSIONS_DIR.iterdir()):
            if not child.is_dir():
                continue
            jar = child / f"{child.name}.jar"
            profile = child / f"{child.name}.json"
            if not jar.exists() and not profile.exists():
                continue
            size = jar.stat().st_size if jar.exists() else 0
            is_of = "optifine" in child.name.lower()
            kind = "OptiFine" if is_of else "Version"
            installed = jar.exists()
            entries.append({
                "id": child.name, "size": size, "kind": kind,
                "installed": installed,
            })
        entries.sort(key=lambda e: parse_version_key(e["id"]), reverse=True)
        return entries

    def _refresh_installed(self) -> None:
        self.installed_list.clear()
        for entry in self._scan_installed():
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(10)

            info = QVBoxLayout()
            info.setSpacing(1)
            name = QLabel(entry["id"])
            name.setObjectName("valueLabel")
            detail = QLabel(
                f"{entry['kind']} · {human_size(entry['size'])}"
                + ("" if entry["installed"] else " · solo perfil"))
            detail.setObjectName("faint")
            info.addWidget(name)
            info.addWidget(detail)
            layout.addLayout(info, 1)

            play = QPushButton("Jugar")
            play.setObjectName("primaryButton")
            play.setCursor(Qt.CursorShape.PointingHandCursor)
            play.setEnabled(entry["installed"])
            play.clicked.connect(
                lambda _=False, vid=entry["id"]: self.shell.play_version(vid))
            folder = QPushButton("Carpeta")
            folder.setObjectName("ghostButton")
            folder.setCursor(Qt.CursorShape.PointingHandCursor)
            folder.clicked.connect(
                lambda _=False, vid=entry["id"]: _open_path(
                    paths.version_dir(vid)))
            delete = QPushButton("Eliminar")
            delete.setObjectName("dangerButton")
            delete.setCursor(Qt.CursorShape.PointingHandCursor)
            delete.clicked.connect(
                lambda _=False, vid=entry["id"]: self.shell.delete_version(vid))
            layout.addWidget(play)
            layout.addWidget(folder)
            layout.addWidget(delete)

            row.ensurePolished()
            item = QListWidgetItem()
            item.setSizeHint(row.sizeHint())
            self.installed_list.addItem(item)
            self.installed_list.setItemWidget(item, row)

        if self.installed_list.count() == 0:
            item = QListWidgetItem("No hay versiones instaladas. "
                                  "Pulsa JUGAR para descargar una.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.installed_list.addItem(item)

    def _refresh_downloads(self) -> None:
        table = self.downloads_table
        table.setRowCount(0)
        for row in database.list_downloads(limit=150):
            r = table.rowCount()
            table.insertRow(r)
            values = [
                _fmt_time(row["ts"]),
                row["kind"],
                row["label"],
                row["version_id"],
                human_size(row["size_bytes"]) if row["size_bytes"] else "-",
                row["status"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setForeground(QColor(theme.COLORS["TEXT_FAINT"]))
                table.setItem(r, c, item)
        if table.rowCount() == 0:
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem(
                "Sin descargas registradas todavia."))
            table.setSpan(0, 0, 1, table.columnCount())

    def _refresh_sessions(self) -> None:
        table = self.sessions_table
        table.setRowCount(0)
        for row in database.list_sessions(limit=150):
            r = table.rowCount()
            table.insertRow(r)
            state = (f"codigo {row['exit_code']}"
                     if row["exit_code"] is not None
                     else _fmt_duration(row["started"], row["ended"]))
            values = [
                _fmt_time(row["started"]),
                row["username"],
                row["version_id"],
                row["account"],
                _fmt_duration(row["started"], row["ended"]),
                state,
            ]
            for c, value in enumerate(values):
                table.setItem(r, c, QTableWidgetItem(str(value)))
        if table.rowCount() == 0:
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem(
                "Aun no has jugado ninguna partida."))
            table.setSpan(0, 0, 1, table.columnCount())

    def _refresh_logs(self) -> None:
        self.logs_list.clear()
        logs = sorted(paths.LOGS_DIR.glob("*.log"),
                      key=lambda p: p.stat().st_mtime, reverse=True)[:30]
        for log in logs:
            stat = log.stat()
            label = (f"{log.name}  ·  {human_size(stat.st_size)}  ·  "
                     f"{time.strftime('%d/%m %H:%M', time.localtime(stat.st_mtime))}")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(log))
            self.logs_list.addItem(item)
        if not logs:
            item = QListWidgetItem("No hay registros todavia.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.logs_list.addItem(item)

    def _open_log(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            _open_path(Path(path))

    def clear_history(self) -> None:
        answer = QMessageBox.question(
            self, "Limpiar historial",
            "Se borrara el historial de descargas y sesiones. "
            "Los archivos del juego no se tocan.\n\n¿Continuar?",
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
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Cuenta")
        title.setObjectName("pageTitle")
        sub = QLabel("Perfil de jugador. Todo funciona sin cuenta; "
                     "Microsoft solo hace falta para servidores oficiales.")
        sub.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch(1)
        self.body.addLayout(head)

        self.body.addWidget(self._offline_card())
        self.body.addWidget(Divider())
        self.body.addWidget(self._microsoft_card())
        self.body.addStretch(1)

    def _offline_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Perfil offline"))
        card.body.addWidget(muted_label(
            "Nombre libre para servidores sin verificacion. "
            "Se genera un UUID offline determinista."))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.off_avatar = Avatar(54)
        column = QVBoxLayout()
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

        use = QPushButton("Usar perfil offline")
        use.setObjectName("primaryButton")
        use.setCursor(Qt.CursorShape.PointingHandCursor)
        use.clicked.connect(self._use_offline)
        card.body.addWidget(use)
        return card

    def _microsoft_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        head = QHBoxLayout()
        head.addWidget(section_label("Cuenta Microsoft"))
        head.addStretch(1)
        self.ms_status = Pill("SIN SESION", dim=True)
        head.addWidget(self.ms_status)
        card.body.addLayout(head)
        card.body.addWidget(muted_label(
            "Inicia sesion con tu cuenta de Microsoft para jugar en "
            "servidores oficiales (online-mode). El launcher nunca ve tu "
            "contrasena: usa el codigo de dispositivo de Microsoft."))

        self.login_button = QPushButton("Iniciar sesion con Microsoft")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_button.clicked.connect(self._start_login)
        card.body.addWidget(self.login_button)

        card.body.addWidget(section_label("Cuentas guardadas"))
        self.accounts_list = QListWidget()
        self.accounts_list.setMinimumHeight(110)
        self.accounts_list.setMaximumHeight(210)
        card.body.addWidget(self.accounts_list)
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

    def refresh_accounts(self) -> None:
        accounts = database.list_accounts()
        active = (self.shell.settings.active_account or "")
        self.ms_status.setText(
            "CONECTADA" if any(f"ms:{a['mc_uuid']}" == active
                               for a in accounts) else "SIN SESION")
        self.accounts_list.clear()
        if not accounts:
            item = QListWidgetItem("No hay cuentas Microsoft guardadas.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.accounts_list.addItem(item)
            return
        for account in accounts:
            key = f"ms:{account['mc_uuid']}"
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(6, 4, 6, 4)
            layout.setSpacing(10)

            info = QVBoxLayout()
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
                badge = Pill("ACTIVA")
                layout.addWidget(badge)
            else:
                use = QPushButton("Usar")
                use.setObjectName("primaryButton")
                use.setCursor(Qt.CursorShape.PointingHandCursor)
                use.clicked.connect(
                    lambda _=False, k=key: self._use_account(k))
                layout.addWidget(use)
            remove = QPushButton("Quitar")
            remove.setObjectName("dangerButton")
            remove.setCursor(Qt.CursorShape.PointingHandCursor)
            remove.clicked.connect(
                lambda _=False, aid=account["mc_uuid"]:
                self._remove_account(aid))
            layout.addWidget(remove)

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
            f"Se eliminara la cuenta {mc_uuid} de este equipo.\n\n"
            "¿Continuar?",
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


class MSLoginDialog(QDialog):
    """Muestra el codigo de dispositivo mientras el worker espera."""

    cancel_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Iniciar sesion con Microsoft")
        self.setModal(True)
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        self.status = QLabel("Solicitando codigo a Microsoft…")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.code_label = QLabel("")
        self.code_label.setObjectName("pageTitle")
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

        open_button = QPushButton("Abrir pagina de Microsoft")
        open_button.setObjectName("primaryButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self._open_link)
        layout.addWidget(open_button)

        self.wait_label = muted_label(
            "Despues de iniciar sesion, este launcher continuara solo.")
        self.wait_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wait_label)
        self.wait_label.setVisible(False)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.setObjectName("ghostButton")
        cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel.clicked.connect(self._cancel)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self._device = None

    def show_code(self, device: msauth.DeviceCode) -> None:
        self._device = device
        self.code_label.setText(device.user_code)
        self.status.setText("Introduce este codigo en la pagina de Microsoft:")
        link = (f"<a href='{device.verification_uri}' style='color:#3DDC97'>"
                f"{device.verification_uri}</a>")
        self.link_label.setText(link)
        self.link_label.setOpenExternalLinks(True)
        self.wait_label.setVisible(True)

    def show_error(self, message: str) -> None:
        self.status.setText(message)
        self.status.setStyleSheet("color: #FF6B6B;")
        self.code_label.setText("")
        self.link_label.setText("")
        self.wait_label.setVisible(False)

    def _open_link(self) -> None:
        if self._device and self._device.verification_uri:
            QDesktopServices.openUrl(
                QUrl(self._device.verification_uri))

    def _cancel(self) -> None:
        self.cancel_requested.emit()
        self.reject()


# =============================================================== AJUSTES
class SettingsPage(ScrollPage):
    def __init__(self, shell: "MainWindow") -> None:
        super().__init__()
        self.shell = shell
        self._build()

    def _build(self) -> None:
        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Ajustes")
        title.setObjectName("pageTitle")
        sub = QLabel("Java, red, rendimiento y video del launcher.")
        sub.setObjectName("pageSubtitle")
        titles.addWidget(title)
        titles.addWidget(sub)
        head.addLayout(titles)
        head.addStretch(1)
        self.body.addLayout(head)

        settings = self.shell.settings
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        java_row = QWidget()
        java_layout = QHBoxLayout(java_row)
        java_layout.setContentsMargins(0, 0, 0, 0)
        java_layout.setSpacing(8)
        self.java_edit = QLineEdit(settings.java_path)
        self.java_edit.setPlaceholderText("Deteccion automatica (javaw.exe)")
        browse = QPushButton("Examinar…")
        browse.setObjectName("ghostButton")
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse_java)
        java_layout.addWidget(self.java_edit, 1)
        java_layout.addWidget(browse)
        form.addRow("Ruta de Java", java_row)

        self.auto_java = QCheckBox("Descargar Temurin automaticamente si falta Java")
        self.auto_java.setChecked(settings.auto_download_java)
        form.addRow("", self.auto_java)

        self.jvm_edit = QLineEdit(settings.extra_jvm_args)
        self.jvm_edit.setPlaceholderText("Ej: -XX:+UseG1GC -Dfile.encoding=UTF-8")
        form.addRow("Argumentos JVM", self.jvm_edit)

        self.show_all = QCheckBox("Mostrar todas las versiones del manifiesto")
        self.show_all.setChecked(settings.show_all_versions)
        form.addRow("", self.show_all)

        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Java y arranque"))
        card.body.addLayout(form)

        detected = java_module.find_runtimes()
        if detected:
            summary = " · ".join(
                f"Java {item.major} ({item.source})" for item in detected[:4]
            )
        else:
            summary = "No se detecto ningun Java instalado."
        card.body.addWidget(faint_label(f"Detectados: {summary}"))
        card.body.addWidget(faint_label(
            f"Hardware: {hardware.summary()} · RAM sugerida: "
            f"{hardware.recommended_memory_mb()} MB"))
        self.body.addWidget(card)

        self.body.addWidget(self._performance_card())
        self.body.addWidget(self._video_card())
        self.body.addWidget(self._data_card())

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        save = QPushButton("Guardar ajustes")
        save.setObjectName("primaryButton")
        save.setCursor(Qt.CursorShape.PointingHandCursor)
        save.clicked.connect(self._save)
        save_row.addWidget(save)
        self.body.addLayout(save_row)
        self.body.addStretch(1)

    def _performance_card(self) -> Card:
        settings = self.shell.settings
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Rendimiento"))

        perf_row = QHBoxLayout()
        perf_row.setSpacing(8)
        perf_row.addWidget(faint_label("Prioridad"))
        self.priority_combo = QComboBox()
        for value, label in (("idle", "Reposo"),
                             ("below_normal", "Baja"),
                             ("normal", "Normal"),
                             ("above_normal", "Alta"),
                             ("high", "Muy alta")):
            self.priority_combo.addItem(label, value)
        self.priority_combo.setToolTip(
            "Prioridad del proceso de Java. Baja/reposo reduce el impacto "
            "en el resto del sistema."
        )
        index = self.priority_combo.findData(settings.game_priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        perf_row.addWidget(self.priority_combo, 1)
        perf_row.addWidget(faint_label("GC"))
        self.gc_combo = QComboBox()
        for value, label in (("auto", "Automatico"),
                             ("g1", "G1GC"),
                             ("serial", "Serial"),
                             ("parallel", "Parallel")):
            self.gc_combo.addItem(label, value)
        self.gc_combo.setToolTip(
            "Recolector de basura de la JVM. Serial consume menos CPU y RAM "
            "en equipos modestos; G1 suele dar mejor rendimiento."
        )
        index = self.gc_combo.findData(settings.gc_preset)
        if index >= 0:
            self.gc_combo.setCurrentIndex(index)
        perf_row.addWidget(self.gc_combo, 1)
        card.body.addLayout(perf_row)

        cores_row = QHBoxLayout()
        cores_row.setSpacing(8)
        cores_row.addWidget(faint_label("Nucleos CPU"))
        self.cores_spin = QSpinBox()
        max_cores = os.cpu_count() or 32
        self.cores_spin.setRange(0, max_cores)
        self.cores_spin.setSpecialValueText("Todos")
        self.cores_spin.setValue(max(0, min(max_cores,
                                            settings.cpu_cores)))
        self.cores_spin.setToolTip(
            "Limita el juego a N nucleos logicos (0 = usar todos)."
        )
        cores_row.addWidget(self.cores_spin)
        cores_row.addStretch(1)
        card.body.addLayout(cores_row)
        return card

    def _video_card(self) -> Card:
        settings = self.shell.settings
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Video"))

        res_row = QHBoxLayout()
        res_row.setSpacing(8)
        res_row.addWidget(faint_label("Resolucion"))
        self.res_width = QSpinBox()
        self.res_width.setRange(0, 7680)
        self.res_width.setSpecialValueText("Auto")
        self.res_width.setSuffix(" px")
        self.res_width.setValue(max(0, settings.resolution_width))
        self.res_width.setToolTip("Ancho en pixeles (0 = automatico)")
        res_row.addWidget(self.res_width)
        self.res_height = QSpinBox()
        self.res_height.setRange(0, 4320)
        self.res_height.setSpecialValueText("Auto")
        self.res_height.setSuffix(" px")
        self.res_height.setValue(max(0, settings.resolution_height))
        self.res_height.setToolTip("Alto en pixeles (0 = automatico)")
        res_row.addWidget(self.res_height)
        res_row.addStretch(1)
        card.body.addLayout(res_row)

        dist_row = QHBoxLayout()
        dist_row.setSpacing(8)
        dist_row.addWidget(faint_label("Distancia render"))
        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(0, 32)
        self.dist_spin.setSpecialValueText("Auto")
        self.dist_spin.setValue(max(0, min(32, settings.render_distance)))
        self.dist_spin.setToolTip(
            "Chunks de distancia de renderizado. Menos = mas FPS y menos RAM "
            "en GPUs integradas (Intel UHD)."
        )
        dist_row.addWidget(self.dist_spin)
        dist_row.addStretch(1)
        card.body.addLayout(dist_row)

        self.gpu_check = QCheckBox("Aceleracion GPU (OpenGL)")
        self.gpu_check.setChecked(settings.gpu_accel)
        self.gpu_check.setToolTip(
            "Pipeline OpenGL de Java2D. Recomendado para Intel UHD e iGPU; "
            "desactivalo solo si el juego no arranca o falla el render."
        )
        card.body.addWidget(self.gpu_check)
        return card

    def _data_card(self) -> Card:
        card = Card(margins=12, spacing=8)
        card.body.addWidget(section_label("Datos"))
        data = QLabel(str(paths.DATA_DIR))
        data.setObjectName("mono")
        data.setWordWrap(True)
        data.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        card.body.addWidget(data)
        row = QHBoxLayout()
        open_data = QPushButton("Abrir carpeta de datos")
        open_data.setObjectName("ghostButton")
        open_data.setCursor(Qt.CursorShape.PointingHandCursor)
        open_data.clicked.connect(lambda: _open_path(paths.DATA_DIR))
        row.addWidget(open_data)
        row.addStretch(1)
        card.body.addLayout(row)
        card.body.addWidget(faint_label(
            f"{APP_NAME} {APP_VERSION} · portable · assets y manifiestos "
            "oficiales de Mojang"))
        return card

    # ------------------------------------------------------------ acciones
    def _browse_java(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ejecutable de Java", "",
            "Ejecutable de Java (*.exe);;Todos los archivos (*)",
        )
        if selected:
            self.java_edit.setText(selected)

    def _save(self) -> None:
        settings = self.shell.settings
        settings.java_path = self.java_edit.text().strip()
        settings.auto_download_java = self.auto_java.isChecked()
        settings.extra_jvm_args = self.jvm_edit.text().strip()
        reload_needed = (self.show_all.isChecked()
                         != settings.show_all_versions)
        settings.show_all_versions = self.show_all.isChecked()
        settings.game_priority = self.priority_combo.currentData()
        settings.gc_preset = self.gc_combo.currentData()
        settings.cpu_cores = self.cores_spin.value()
        settings.resolution_width = self.res_width.value()
        settings.resolution_height = self.res_height.value()
        settings.render_distance = self.dist_spin.value()
        settings.gpu_accel = self.gpu_check.isChecked()
        self.shell._save_settings()
        if reload_needed:
            self.shell._reload_versions()
        self.shell.console.append("Ajustes guardados.")
        self.shell._set_status("Ajustes guardados.", "ok")
