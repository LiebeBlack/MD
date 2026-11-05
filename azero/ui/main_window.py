"""Ventana principal y ajustes del launcher AZeroCraft."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
                             QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                             QLineEdit, QMainWindow, QMessageBox, QProgressBar,
                             QPushButton, QSlider, QSpinBox, QVBoxLayout,
                             QWidget)

from .. import (APP_NAME, APP_VERSION, hardware, java as java_module,
                optifine, paths)
from ..auth import offline_uuid, validate_username
from ..constants import MAX_MEMORY_MB, MEMORY_STEP_MB, MIN_MEMORY_MB
from ..manifest import load_version_profile, local_profiles, parse_version_key
from ..settings import Settings
from ..workers import LaunchWorker, ManifestWorker, OptiFineWorker
from . import theme
from .widgets import (Avatar, Card, ConsoleView, Divider, Pill, faint_label,
                      muted_label, section_label)


def _repolish(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def _gb_text(memory_mb: int) -> str:
    value = memory_mb / 1024
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text} GB"


def _java_major_for(version_id: str) -> int:
    """Java recomendado si el perfil aun no esta descargado (heuristica)."""
    key = parse_version_key(version_id)
    if key >= (1, 20, 5):
        return 21
    if key >= (1, 17, 0):
        return 17
    return 8


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


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Ajustes")
        title.setObjectName("brandTitle")
        title.setStyleSheet("font-size: 17pt;")
        layout.addWidget(title)
        layout.addWidget(faint_label("Java, red y opciones avanzadas del launcher."))

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        java_row = QWidget()
        java_layout = QHBoxLayout(java_row)
        java_layout.setContentsMargins(0, 0, 0, 0)
        java_layout.setSpacing(8)
        self.java_edit = QLineEdit(settings.java_path)
        self.java_edit.setPlaceholderText("Deteccion automatica (javaw.exe)")
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self._browse_java)
        java_layout.addWidget(self.java_edit, 1)
        java_layout.addWidget(browse)
        form.addRow("Ruta de Java", java_row)

        self.auto_java = QCheckBox("Descargar Temurin automaticamente si falta Java")
        self.auto_java.setChecked(settings.auto_download_java)
        form.addRow("", self.auto_java)

        self.server_edit = QLineEdit(settings.server)
        self.server_edit.setPlaceholderText("play.servidor.net:25565")
        form.addRow("Conexion rapida", self.server_edit)

        self.jvm_edit = QLineEdit(settings.extra_jvm_args)
        self.jvm_edit.setPlaceholderText("Ej: -XX:+UseG1GC -Dfile.encoding=UTF-8")
        form.addRow("Argumentos JVM", self.jvm_edit)

        self.show_all = QCheckBox("Mostrar todas las versiones del manifiesto")
        self.show_all.setChecked(settings.show_all_versions)
        form.addRow("", self.show_all)

        layout.addLayout(form)

        detected = java_module.find_runtimes()
        if detected:
            summary = " · ".join(
                f"Java {item.major} ({item.source})" for item in detected[:4]
            )
        else:
            summary = "No se detecto ningun Java instalado."
        layout.addWidget(faint_label(f"Detectados: {summary}"))
        layout.addWidget(faint_label(
            f"Hardware: {hardware.summary()} · RAM sugerida: "
            f"{hardware.recommended_memory_mb()} MB"
        ))
        layout.addWidget(Divider())

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Guardar")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    def _browse_java(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar ejecutable de Java", "",
            "Ejecutable de Java (*.exe);;Todos los archivos (*)",
        )
        if selected:
            self.java_edit.setText(selected)

    def values(self) -> dict:
        return {
            "java_path": self.java_edit.text().strip(),
            "auto_download_java": self.auto_java.isChecked(),
            "server": self.server_edit.text().strip(),
            "extra_jvm_args": self.jvm_edit.text().strip(),
            "show_all_versions": self.show_all.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self._entries: list[dict] = []
        self._manifest_worker: ManifestWorker | None = None
        self._launch_worker: LaunchWorker | None = None
        self._of_worker: OptiFineWorker | None = None
        self._titlebar_done = False
        self._allow_close = False

        self.setWindowTitle(f"{APP_NAME} Launcher")
        self.resize(1080, 760)
        self.setMinimumSize(980, 720)

        self._build_ui()
        self._apply_settings()
        self._refresh_account()
        self._reload_versions()

        shortcut = QShortcut(QKeySequence("Ctrl+,"), self)
        shortcut.activated.connect(self._open_settings)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 16, 20, 12)
        outer.setSpacing(12)
        outer.addLayout(self._build_header())
        outer.addLayout(self._build_body(), 1)
        outer.addLayout(self._build_footer())

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(14)

        icon = QLabel()
        icon.setPixmap(theme.app_icon().pixmap(36, 36))
        icon.setFixedSize(36, 36)
        row.addWidget(icon)

        titles = QVBoxLayout()
        titles.setSpacing(0)
        brand = QLabel(
            '<span style="color:#E7EEF9">AZero</span>'
            '<span style="color:#3DE0A0">Craft</span>'
        )
        brand.setObjectName("brandTitle")
        brand.setTextFormat(Qt.TextFormat.RichText)
        subtitle = QLabel("LAUNCHER LIGERO · MINECRAFT 1.8 – 1.15.2")
        subtitle.setObjectName("faint")
        titles.addWidget(brand)
        titles.addWidget(subtitle)
        row.addLayout(titles)
        row.addStretch(1)
        row.addWidget(Pill("Modo offline"))

        settings_button = QPushButton("⚙")
        settings_button.setObjectName("iconButton")
        settings_button.setFixedSize(38, 38)
        settings_button.setToolTip("Ajustes (Ctrl+,)")
        settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_button.clicked.connect(self._open_settings)
        row.addWidget(settings_button)
        return row

    def _build_body(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(18)

        left_widget = QWidget()
        left_widget.setFixedWidth(372)
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(0, 0, 0, 0)
        left.setSpacing(10)
        left.addWidget(self._build_account_card())
        left.addWidget(self._build_version_card())
        left.addWidget(self._build_options_card())
        left.addStretch(1)

        self.play_button = QPushButton("JUGAR")
        self.play_button.setObjectName("playButton")
        self.play_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_button.setMinimumHeight(48)
        self.play_button.clicked.connect(self._on_play_clicked)
        left.addWidget(self.play_button)

        self.status_label = QLabel("Listo para jugar.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        left.addWidget(self.status_label)

        body.addWidget(left_widget)
        body.addWidget(self._build_console_card(), 1)
        return body

    def _build_account_card(self) -> Card:
        card = Card(margins=14, spacing=10)
        card.body.addWidget(section_label("Cuenta"))

        row = QHBoxLayout()
        row.setSpacing(14)
        self.avatar = Avatar(50)
        column = QVBoxLayout()
        column.setSpacing(2)
        self.name_edit = QLineEdit(self.settings.username)
        self.name_edit.setObjectName("nameEdit")
        self.name_edit.setMaxLength(16)
        self.name_edit.setPlaceholderText("Nombre de jugador")
        self.name_edit.textChanged.connect(self._refresh_account)
        self.uuid_label = QLabel()
        self.uuid_label.setObjectName("mono")
        column.addWidget(self.name_edit)
        column.addWidget(self.uuid_label)
        row.addWidget(self.avatar)
        row.addLayout(column, 1)
        card.body.addLayout(row)

        footer = QHBoxLayout()
        footer.addWidget(Pill("SIN CUENTAS", dim=True))
        footer.addStretch(1)
        footer.addWidget(faint_label("UUID v3 determinista"))
        card.body.addLayout(footer)
        return card

    def _build_version_card(self) -> Card:
        card = Card(margins=14, spacing=10)
        card.body.addWidget(section_label("Versión"))

        self.version_combo = QComboBox()
        self.version_combo.setPlaceholderText("Cargando versiones…")
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        card.body.addWidget(self.version_combo)

        self.version_meta = muted_label("Leyendo el manifiesto oficial de Mojang…")
        card.body.addWidget(self.version_meta)
        card.body.addWidget(Divider())

        row = QHBoxLayout()
        row.setSpacing(10)
        column = QVBoxLayout()
        column.setSpacing(2)
        title = QLabel("OptiFine")
        title.setObjectName("valueLabel")
        self.optifine_status = faint_label("Comprobando estado…")
        column.addWidget(title)
        column.addWidget(self.optifine_status)
        self.optifine_button = QPushButton("Instalar…")
        self.optifine_button.setObjectName("accentGhost")
        self.optifine_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.optifine_button.clicked.connect(self._on_install_optifine)
        row.addLayout(column, 1)
        row.addWidget(self.optifine_button)
        card.body.addLayout(row)
        return card

    def _build_options_card(self) -> Card:
        card = Card(margins=14, spacing=10)

        head = QHBoxLayout()
        head.addWidget(section_label("Memoria RAM"))
        head.addStretch(1)
        self.ram_value = QLabel(_gb_text(self.settings.memory_mb))
        self.ram_value.setObjectName("valueLabel")
        head.addWidget(self.ram_value)
        card.body.addLayout(head)

        self.ram_slider = QSlider(Qt.Orientation.Horizontal)
        self.ram_slider.setMinimum(MIN_MEMORY_MB)
        self.ram_slider.setMaximum(MAX_MEMORY_MB)
        self.ram_slider.setSingleStep(MEMORY_STEP_MB)
        self.ram_slider.setPageStep(1024)
        self.ram_slider.valueChanged.connect(self._on_ram_changed)
        self.ram_slider.sliderReleased.connect(self._save_settings)
        card.body.addWidget(self.ram_slider)

        self.server_edit = QLineEdit(self.settings.server)
        self.server_edit.setPlaceholderText("Servidor opcional: play.ejemplo.net:25565")
        self.server_edit.editingFinished.connect(self._on_server_changed)
        card.body.addWidget(self.server_edit)

        self.auto_close_check = QCheckBox("Cerrar el launcher al iniciar el juego")
        self.auto_close_check.setChecked(self.settings.auto_close)
        self.auto_close_check.setToolTip(
            "El juego se ejecuta en un proceso independiente, por lo que el "
            "launcher puede cerrarse y liberar toda su memoria."
        )
        self.auto_close_check.toggled.connect(self._on_auto_close_changed)
        card.body.addWidget(self.auto_close_check)
        card.body.addWidget(faint_label("0% de consumo en segundo plano tras inyectar el juego."))

        card.body.addWidget(Divider())
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
        self.priority_combo.currentIndexChanged.connect(self._on_priority_changed)
        perf_row.addWidget(self.priority_combo, 1)
        perf_row.addWidget(faint_label("GC"))
        self.gc_combo = QComboBox()
        for value, label in (("auto", "Automático"),
                             ("g1", "G1GC"),
                             ("serial", "Serial"),
                             ("parallel", "Parallel")):
            self.gc_combo.addItem(label, value)
        self.gc_combo.setToolTip(
            "Recolector de basura de la JVM. Serial consume menos CPU y RAM "
            "en equipos modestos; G1 suele dar mejor rendimiento."
        )
        self.gc_combo.currentIndexChanged.connect(self._on_gc_changed)
        perf_row.addWidget(self.gc_combo, 1)
        card.body.addLayout(perf_row)

        cores_row = QHBoxLayout()
        cores_row.setSpacing(8)
        cores_row.addWidget(faint_label("Núcleos CPU"))
        self.cores_spin = QSpinBox()
        max_cores = os.cpu_count() or 32
        self.cores_spin.setRange(0, max_cores)
        self.cores_spin.setSpecialValueText("Todos")
        self.cores_spin.setToolTip(
            "Limita el juego a N núcleos lógicos (0 = usar todos)."
        )
        self.cores_spin.valueChanged.connect(self._on_cores_changed)
        cores_row.addWidget(self.cores_spin)
        cores_row.addStretch(1)
        card.body.addLayout(cores_row)

        card.body.addWidget(Divider())
        card.body.addWidget(section_label("Vídeo"))

        res_row = QHBoxLayout()
        res_row.setSpacing(8)
        res_row.addWidget(faint_label("Resolución"))
        self.res_width = QSpinBox()
        self.res_width.setRange(0, 7680)
        self.res_width.setSpecialValueText("Auto")
        self.res_width.setSuffix(" px")
        self.res_width.setToolTip("Ancho en píxeles (0 = automático)")
        self.res_width.valueChanged.connect(self._on_resolution_changed)
        res_row.addWidget(self.res_width)
        self.res_height = QSpinBox()
        self.res_height.setRange(0, 4320)
        self.res_height.setSpecialValueText("Auto")
        self.res_height.setSuffix(" px")
        self.res_height.setToolTip("Alto en píxeles (0 = automático)")
        self.res_height.valueChanged.connect(self._on_resolution_changed)
        res_row.addWidget(self.res_height)
        res_row.addStretch(1)
        card.body.addLayout(res_row)

        dist_row = QHBoxLayout()
        dist_row.setSpacing(8)
        dist_row.addWidget(faint_label("Distancia render"))
        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(0, 32)
        self.dist_spin.setSpecialValueText("Auto")
        self.dist_spin.setToolTip(
            "Chunks de distancia de renderizado. Menos = más FPS y menos RAM "
            "en GPUs integradas (Intel UHD)."
        )
        self.dist_spin.valueChanged.connect(self._on_render_distance_changed)
        dist_row.addWidget(self.dist_spin)
        dist_row.addStretch(1)
        card.body.addLayout(dist_row)

        self.gpu_check = QCheckBox("Aceleración GPU (OpenGL)")
        self.gpu_check.setChecked(self.settings.gpu_accel)
        self.gpu_check.setToolTip(
            "Pipeline OpenGL de Java2D. Recomendado para Intel UHD e iGPU; "
            "desactívalo solo si el juego no arranca o falla el render."
        )
        self.gpu_check.toggled.connect(self._on_gpu_toggled)
        card.body.addWidget(self.gpu_check)
        return card

    def _build_console_card(self) -> Card:
        card = Card(margins=14, spacing=10)

        head = QHBoxLayout()
        head.addWidget(section_label("Registro"))
        head.addStretch(1)
        open_folder = QPushButton("Carpeta")
        open_folder.setObjectName("ghostButton")
        open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        open_folder.clicked.connect(self._open_mc_folder)
        clear = QPushButton("Limpiar")
        clear.setObjectName("ghostButton")
        clear.setCursor(Qt.CursorShape.PointingHandCursor)
        clear.clicked.connect(lambda: self.console.clear())
        head.addWidget(open_folder)
        head.addWidget(clear)
        card.body.addLayout(head)

        self.console = ConsoleView()
        card.body.addWidget(self.console, 1)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
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
        card.body.addLayout(progress_row)

        self.stage_label = muted_label("Esperando acción.")
        self.stage_label.setWordWrap(True)
        card.body.addWidget(self.stage_label)
        return card

    def _build_footer(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        row.addWidget(faint_label(f"{APP_NAME} {APP_VERSION} · portable"))
        row.addWidget(faint_label("·"))
        data = QLabel(f"datos en {paths.DATA_DIR}")
        data.setObjectName("faint")
        data.setToolTip(str(paths.DATA_DIR))
        row.addWidget(data)
        row.addStretch(1)
        row.addWidget(faint_label("Assets y manifiestos oficiales de Mojang"))
        return row

    # -------------------------------------------------------------- estado
    def _launch_running(self) -> bool:
        return bool(self._launch_worker and self._launch_worker.isRunning())

    def _of_running(self) -> bool:
        return bool(self._of_worker and self._of_worker.isRunning())

    def _is_busy(self) -> bool:
        return self._launch_running() or self._of_running()

    def _selected_version(self) -> str:
        return self.version_combo.currentData() or ""

    def _selected_base(self) -> str:
        version_id = self._selected_version()
        if not version_id:
            return ""
        payload = load_version_profile(version_id) or {}
        return payload.get("inheritsFrom") or version_id

    def _refresh_state(self) -> None:
        busy = self._is_busy()
        has_version = self.version_combo.count() > 0
        self.name_edit.setEnabled(not busy)
        self.version_combo.setEnabled(not busy)
        self.optifine_button.setEnabled(not busy and has_version)
        self.ram_slider.setEnabled(not busy)
        self.auto_close_check.setEnabled(not busy)
        self.server_edit.setEnabled(not busy)
        self.priority_combo.setEnabled(not busy)
        self.gc_combo.setEnabled(not busy)
        self.cores_spin.setEnabled(not busy)
        self.res_width.setEnabled(not busy)
        self.res_height.setEnabled(not busy)
        self.dist_spin.setEnabled(not busy)
        self.gpu_check.setEnabled(not busy)

        valid_name = validate_username(self.name_edit.text().strip()) is None
        if self._launch_running():
            self.play_button.setText("CANCELAR")
            self.play_button.setEnabled(True)
        elif self._of_running():
            self.play_button.setText("INSTALANDO…")
            self.play_button.setEnabled(False)
        else:
            self.play_button.setText("JUGAR")
            self.play_button.setEnabled(valid_name and has_version)

        busy_property = busy
        if bool(self.play_button.property("busy")) != busy_property:
            self.play_button.setProperty("busy", busy_property)
            _repolish(self.play_button)

    def _set_status(self, text: str, kind: str = "normal") -> None:
        mapping = {"normal": "statusLabel", "error": "statusError", "ok": "statusOk"}
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
        if not hasattr(self, "name_edit"):
            return
        name = self.name_edit.text().strip()
        error = validate_username(name)
        if error:
            self.avatar.set_identity(name or "?", name or "?")
            self.uuid_label.setText("UUID pendiente")
            self.uuid_label.setToolTip(error)
        else:
            uuid = offline_uuid(name)
            self.avatar.set_identity(name, uuid)
            self.uuid_label.setText(f"UUID {uuid}")
            self.uuid_label.setToolTip("UUID offline v3 (Java nameUUIDFromBytes)")
        self._refresh_state()
        if not error and not self._is_busy() and not self.version_combo.count():
            self._set_status("Cargando versiones…")

    def _apply_settings(self) -> None:
        self.ram_slider.setValue(max(MIN_MEMORY_MB, min(MAX_MEMORY_MB,
                                                        self.settings.memory_mb)))
        self.ram_value.setText(_gb_text(self.ram_slider.value()))
        self.auto_close_check.setChecked(self.settings.auto_close)
        self.server_edit.setText(self.settings.server)
        self.name_edit.setText(self.settings.username)

        index = self.priority_combo.findData(self.settings.game_priority)
        if index >= 0:
            self.priority_combo.setCurrentIndex(index)
        index = self.gc_combo.findData(self.settings.gc_preset)
        if index >= 0:
            self.gc_combo.setCurrentIndex(index)
        self.cores_spin.setValue(max(0, min(self.cores_spin.maximum(),
                                            self.settings.cpu_cores)))
        self.res_width.setValue(max(0, self.settings.resolution_width))
        self.res_height.setValue(max(0, self.settings.resolution_height))
        self.dist_spin.setValue(max(0, min(32, self.settings.render_distance)))
        self.gpu_check.setChecked(self.settings.gpu_accel)

    def _save_settings(self) -> None:
        self.settings.memory_mb = self.ram_slider.value()
        self.settings.auto_close = self.auto_close_check.isChecked()
        self.settings.server = self.server_edit.text().strip()
        self.settings.username = self.name_edit.text().strip()
        self.settings.version = self._selected_version() or self.settings.version
        try:
            self.settings.save()
        except OSError as error:
            self.console.append(f"No se pudieron guardar los ajustes: {error}")

    # ------------------------------------------------------------ versiones
    def _reload_versions(self) -> None:
        if self._manifest_worker and self._manifest_worker.isRunning():
            return
        self.version_meta.setText("Actualizando el manifiesto oficial…")
        worker = ManifestWorker(self.settings.show_all_versions, self)
        worker.ready.connect(self._on_manifest_ready)
        worker.failed.connect(self._on_manifest_failed)
        worker.finished.connect(self._on_manifest_finished)
        self._manifest_worker = worker
        worker.start()

    def _on_manifest_ready(self, entries: list[dict]) -> None:
        self._entries = entries
        current = self.settings.version
        self.version_combo.blockSignals(True)
        self.version_combo.clear()
        for entry in entries:
            label = entry["id"]
            if entry.get("local"):
                label += "  · OptiFine" if "optifine" in label.lower() else "  · local"
            self.version_combo.addItem(label, entry["id"])
        index = self.version_combo.findData(current)
        if index < 0:
            # Preferir una version ya descargada (juego inmediato) sobre el
            # maximo del manifiesto.
            installed = sorted(local_profiles(),
                               key=parse_version_key, reverse=True)
            index = -1
            for profile_id in installed:
                index = self.version_combo.findData(profile_id)
                if index >= 0:
                    break
            if index < 0:
                preferred = self.version_combo.findData("1.15.2")
                index = preferred if preferred >= 0 else 0
        if self.version_combo.count():
            self.version_combo.setCurrentIndex(index)
            self.settings.version = self.version_combo.currentData()
        self.version_combo.blockSignals(False)
        self.version_combo.setEnabled(True)
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
            self.version_meta.setText("Sin versiones cargadas.")
            return
        base = self._selected_base()
        payload = load_version_profile(version_id) or {}
        is_optifine = "optifine" in version_id.lower()
        kind = "OptiFine" if is_optifine else ("Perfil local" if payload.get("inheritsFrom") else "Vanilla")
        if paths.version_jar_path(base).exists():
            state = "instalada"
        else:
            state = "se descargará al jugar"
        self.version_meta.setText(
            f"{base} · Java {_java_major_display(version_id)} · {kind} · {state}"
        )
        self._update_optifine_row(base)

    def _update_optifine_row(self, base: str) -> None:
        profiles = [pid for pid in local_profiles()
                    if base and pid.startswith(f"{base}-OptiFine_")]
        if profiles:
            edition = profiles[0].split("OptiFine_", 1)[-1].replace("_", " ")
            self.optifine_status.setText(f"Instalado · {edition}")
            self.optifine_button.setText("Reinstalar…")
        else:
            self.optifine_status.setText("No instalado · más FPS y shaders")
            self.optifine_button.setText("Instalar…")

    # --------------------------------------------------------------- juego
    def _on_play_clicked(self) -> None:
        if self._launch_running():
            if self._launch_worker:
                self._launch_worker.cancel()
            self.play_button.setEnabled(False)
            self._set_status("Cancelando…")
            return
        if self._is_busy():
            return

        name = self.name_edit.text().strip()
        error = validate_username(name)
        if error:
            QMessageBox.warning(self, "Nombre inválido", error)
            return
        version_id = self._selected_version()
        if not version_id:
            QMessageBox.warning(self, "Sin versión", "Selecciona una versión de Minecraft.")
            return

        self.settings.username = name
        self.settings.version = version_id
        self._save_settings()
        self.console.append(f"=== {version_id} · {name} ===")
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
        self._save_settings()
        if auto_close:
            self.console.append("Autocierre activo: el launcher se cerrará ahora.")
            QTimer.singleShot(1200, self._quit_after_launch)

    def _quit_after_launch(self) -> None:
        self._allow_close = True
        self.close()
        QApplication.instance().quit()

    def _on_game_exit(self, code: int) -> None:
        self.console.append(f"Minecraft finalizó (código {code}).")
        if not self._allow_close:
            self._set_status(f"Minecraft se cerró (código {code}).", "normal")

    def _on_failed(self, message: str) -> None:
        self.console.append(f"ERROR: {message}")
        first_line = message.strip().splitlines()[0] if message.strip() else "Error desconocido"
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
            info = optifine.inspect_installer(installer)
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
        self._set_status(f"{profile_id} listo.", "ok")
        self._reload_versions()

    def _on_optifine_finished(self) -> None:
        worker = self._of_worker
        self._of_worker = None
        if worker:
            worker.deleteLater()
        self._refresh_state()

    # -------------------------------------------------------------- ajustes
    def _on_ram_changed(self, value: int) -> None:
        rounded = int(round(value / MEMORY_STEP_MB) * MEMORY_STEP_MB)
        if rounded != value:
            self.ram_slider.setValue(rounded)
            return
        self.ram_value.setText(_gb_text(value))
        self.settings.memory_mb = value

    def _on_auto_close_changed(self, checked: bool) -> None:
        self.settings.auto_close = checked
        self._save_settings()

    def _on_server_changed(self) -> None:
        self.settings.server = self.server_edit.text().strip()
        self._save_settings()

    def _on_priority_changed(self, index: int) -> None:
        self.settings.game_priority = self.priority_combo.itemData(index)
        self._save_settings()

    def _on_gc_changed(self, index: int) -> None:
        self.settings.gc_preset = self.gc_combo.itemData(index)
        self._save_settings()

    def _on_cores_changed(self, value: int) -> None:
        self.settings.cpu_cores = value
        self._save_settings()

    def _on_resolution_changed(self, _value: int) -> None:
        self.settings.resolution_width = self.res_width.value()
        self.settings.resolution_height = self.res_height.value()
        self._save_settings()

    def _on_render_distance_changed(self, value: int) -> None:
        self.settings.render_distance = value
        self._save_settings()

    def _on_gpu_toggled(self, checked: bool) -> None:
        self.settings.gpu_accel = checked
        self._save_settings()

    def _open_settings(self) -> None:
        if self._is_busy():
            return
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        reload_needed = values["show_all_versions"] != self.settings.show_all_versions
        for key, value in values.items():
            setattr(self.settings, key, value)
        self._save_settings()
        self._apply_settings()
        self._refresh_account()
        if reload_needed:
            self._reload_versions()
        self._set_status("Ajustes guardados.", "ok")

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
        self._save_settings()
        if self._launch_worker and self._launch_worker.isRunning():
            self._launch_worker.cancel()
            self._launch_worker.wait(1500)
        if self._of_worker and self._of_worker.isRunning():
            self._of_worker.cancel()
            self._of_worker.wait(1500)
        super().closeEvent(event)
