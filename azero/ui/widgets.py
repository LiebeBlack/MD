"""Widgets reutilizables de la interfaz."""

from __future__ import annotations

import hashlib
from typing import Callable

from PyQt6.QtCore import QPoint, QRectF, Qt, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import (QColor, QDesktopServices, QFont, QFontDatabase,
                         QLinearGradient, QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPlainTextEdit, QPushButton,
                             QScrollArea, QSlider, QSizePolicy, QTableWidget,
                             QTableWidgetItem, QToolButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

from .. import APP_VERSION
from ..branding import brand_mark, brand_pixmap
from ..manifest import (load_version_profile, parse_version_key,
                        version_family_label)
from . import theme


def repolish(widget: QWidget) -> None:
    """Vuelve a aplicar el QSS tras cambiar una propiedad dinamica."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


_BUTTON_KINDS = {
    "primary": "primaryButton",
    "accent": "accentGhost",
    "ghost": "ghostButton",
    "danger": "dangerButton",
    "icon": "iconButton",
    "segment": "segButton",
    "preset": "presetButton",
}


def make_button(text: str, kind: str = "", tooltip: str = "",
                on_click: Callable[[], None] | None = None,
                parent: QWidget | None = None) -> QPushButton:
    """Boton con el estilo, cursor y tooltip estandar del launcher."""
    button = QPushButton(text, parent)
    object_name = _BUTTON_KINDS.get(kind)
    if object_name:
        button.setObjectName(object_name)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        button.setToolTip(tooltip)
    if on_click is not None:
        button.clicked.connect(lambda _checked=False: on_click())
    return button


def link_button(text: str, url: str, kind: str = "accent",
                tooltip: str = "", parent: QWidget | None = None) -> QPushButton:
    """Boton que abre una URL externa en el navegador."""
    return make_button(
        text, kind, tooltip or url,
        lambda: QDesktopServices.openUrl(QUrl(url)), parent)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None,
                 margins: int = theme.CARD_MARGIN,
                 spacing: int = theme.CARD_SPACING):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(margins, margins, margins, margins)
        self.body.setSpacing(spacing)


class BrandBanner(QWidget):
    """Cabecera visual de Acerca de: fondo de marca, logo y version."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setAccessibleName("AZeroCraft Launcher")
        self._fonts = bool(QFontDatabase.families())

    def paintEvent(self, event) -> None:  # noqa: N802 - API de Qt
        width, height = self.width(), self.height()
        if width <= 0 or height <= 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(0, 0, width, height)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 12, 12)
        painter.setClipPath(clip)

        gradient = QLinearGradient(0, 0, width, height)
        gradient.setColorAt(0.0, QColor("#0B3D73"))
        gradient.setColorAt(0.55, QColor("#0F6CBD"))
        gradient.setColorAt(1.0, QColor("#0A2342"))
        painter.fillRect(rect, gradient)

        painter.setPen(QPen(QColor(255, 255, 255, 11), 1))
        for x in range(-height, width + height, 24):
            painter.drawLine(x, 0, x + height, height)

        painter.save()
        painter.setOpacity(0.11)
        painter.translate(width - 250, 0)
        painter.scale(2.1, 2.1)
        brand_mark(painter, QColor("#FFFFFF"), 22)
        painter.restore()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 236))
        painter.drawRoundedRect(QRectF(20, 24, 72, 72), 18, 18)
        painter.drawPixmap(26, 30, brand_pixmap(60))

        if self._fonts:
            label = QFont("Segoe UI")
            label.setWeight(QFont.Weight.Bold)
            label.setPixelSize(9)
            label.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
            painter.setFont(label)
            painter.setPen(QColor("#A9D2F5"))
            painter.drawText(QRectF(108, 20, 400, 14),
                             Qt.AlignmentFlag.AlignLeft
                             | Qt.AlignmentFlag.AlignVCenter,
                             "ACERCA DE")

            painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(QRectF(108, 34, width - 210, 30),
                             Qt.AlignmentFlag.AlignLeft
                             | Qt.AlignmentFlag.AlignVCenter,
                             "AZeroCraft Launcher")

            subtitle_font = QFont("Segoe UI")
            subtitle_font.setPixelSize(12)
            painter.setFont(subtitle_font)
            painter.setPen(QColor("#C7E2FA"))
            painter.drawText(QRectF(108, 70, width - 210, 18),
                             Qt.AlignmentFlag.AlignLeft
                             | Qt.AlignmentFlag.AlignVCenter,
                             "Launcher de Minecraft Java Edition · "
                             "1.7 – actual")

            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#9CC7F0"))
            painter.drawText(QRectF(108, 92, width - 210, 18),
                             Qt.AlignmentFlag.AlignLeft
                             | Qt.AlignmentFlag.AlignVCenter,
                             "Por Liebe Black · versiones, librerías y "
                             "Java oficiales · offline y Microsoft")

            pill = QRectF(width - 90, 22, 64, 22)
            painter.setPen(QPen(QColor(255, 255, 255, 52), 1))
            painter.setBrush(QColor(255, 255, 255, 28))
            painter.drawRoundedRect(pill, 11, 11)
            painter.setPen(QColor("#FFFFFF"))
            version_font = QFont("Segoe UI")
            version_font.setWeight(QFont.Weight.Bold)
            version_font.setPixelSize(11)
            painter.setFont(version_font)
            painter.drawText(pill, Qt.AlignmentFlag.AlignCenter,
                             f"v{APP_VERSION}")

        painter.end()


class PageHeader(QWidget):
    """Cabecera comun: titulo, subtitulo y acciones alineadas a la derecha."""

    def __init__(self, title: str, subtitle: str = "",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("pageHeader")
        self.row = QHBoxLayout(self)
        self.row.setContentsMargins(0, 0, 0, 2)
        self.row.setSpacing(theme.COLUMN_GAP)

        titles = QVBoxLayout()
        titles.setContentsMargins(0, 0, 0, 0)
        titles.setSpacing(2)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageTitle")
        self.title_label.setWordWrap(True)
        titles.addWidget(self.title_label)
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("pageSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setVisible(bool(subtitle))
        titles.addWidget(self.subtitle_label)
        self.row.addLayout(titles, 1)

        self._actions = QWidget()
        self.action_layout = QHBoxLayout(self._actions)
        self.action_layout.setContentsMargins(0, 0, 0, 0)
        self.action_layout.setSpacing(8)
        self.row.addWidget(self._actions, 0, Qt.AlignmentFlag.AlignVCenter)

    def add_action(self, widget: QWidget) -> QWidget:
        self.action_layout.addWidget(widget)
        return widget


class StatCard(QFrame):
    """Tarjeta compacta de estadistica con valor y leyenda."""

    def __init__(self, caption: str, value: str = "0",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(1)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        self.value_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.caption_label = QLabel(caption.upper())
        self.caption_label.setObjectName("statCaption")
        self.caption_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.value_label)
        layout.addWidget(self.caption_label)

    def set_value(self, text: str) -> None:
        self.value_label.setText(str(text))


class InfoGrid(QWidget):
    """Rejilla clave/valor alineada para informacion del sistema."""

    def __init__(self, rows: list[tuple[str, str]] | None = None,
                 key_width: int = 104, parent: QWidget | None = None):
        super().__init__(parent)
        self._key_width = key_width
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(5)
        self._grid.setColumnStretch(1, 1)
        self._labels: dict[str, QLabel] = {}
        self.set_rows(rows or [])

    def _clear(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_rows(self, rows: list[tuple[str, str]]) -> None:
        self._clear()
        self._labels = {}
        for row, (key, value) in enumerate(rows):
            key_label = QLabel(key)
            key_label.setObjectName("faint")
            key_label.setMinimumWidth(self._key_width)
            key_label.setAlignment(Qt.AlignmentFlag.AlignLeft
                                   | Qt.AlignmentFlag.AlignTop)
            value_label = QLabel(str(value))
            value_label.setObjectName("mono")
            value_label.setWordWrap(True)
            value_label.setAlignment(Qt.AlignmentFlag.AlignLeft
                                     | Qt.AlignmentFlag.AlignTop)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            self._grid.addWidget(key_label, row, 0)
            self._grid.addWidget(value_label, row, 1)
            self._labels[key] = value_label

    def set_value(self, key: str, value: str) -> None:
        label = self._labels.get(key)
        if label is not None:
            label.setText(str(value))


def list_row() -> tuple[QWidget, QHBoxLayout]:
    """Fila estandar para listas con widgets (versiones, cuentas)."""
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(10)
    return row, layout


def set_empty_table_message(table: QTableWidget, text: str) -> None:
    """Muestra un mensaje centrado que ocupa toda la tabla vacia."""
    table.clearSpans()
    table.setRowCount(0)
    table.insertRow(0)
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QColor(theme.COLORS["TEXT_FAINT"]))
    table.setItem(0, 0, item)
    table.setSpan(0, 0, 1, table.columnCount())
    table.setRowHeight(0, 46)


class ScrollPage(QWidget):
    """Pagina con scroll vertical y contenido centrado con ancho maximo.

    Evita que las tarjetas se estiren de borde a borde en monitores grandes
    y que algo se corte en ventanas pequenas.
    """

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
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignHCenter
                                 | Qt.AlignmentFlag.AlignTop)

        self.content = QWidget()
        self.content.setObjectName("page")
        self.content.setMaximumWidth(theme.CONTENT_MAX_WIDTH)
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(theme.PAGE_MARGIN, theme.PAGE_MARGIN,
                                     theme.PAGE_MARGIN, theme.PAGE_MARGIN)
        self.body.setSpacing(theme.PAGE_SPACING)
        self.scroll.setWidget(self.content)
        outer.addWidget(self.scroll)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)


class FocusWheelSlider(QSlider):
    """Slider que ignora la rueda salvo que tenga el foco de teclado."""

    def wheelEvent(self, event) -> None:  # noqa: N802 - API de Qt
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


def section_label(text: str) -> QLabel:
    label = QLabel(text.upper())
    label.setObjectName("sectionLabel")
    return label


def muted_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("muted")
    label.setWordWrap(True)
    return label


def faint_label(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("faint")
    label.setWordWrap(True)
    return label


class Pill(QLabel):
    def __init__(self, text: str, dim: bool = False,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("pillDim" if dim else "pill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText(text)

    def setText(self, text: str) -> None:  # noqa: N802 - API de Qt
        super().setText(str(text).upper())

    def set_dim(self, dim: bool) -> None:
        name = "pillDim" if dim else "pill"
        if self.objectName() != name:
            self.setObjectName(name)
            repolish(self)


class Avatar(QWidget):
    """Avatar generado a partir del UUID, sin descargas externas."""

    def __init__(self, size: int = 52, parent: QWidget | None = None):
        super().__init__(parent)
        self._size = size
        self._initials = "?"
        self._seed = 0
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_identity(self, name: str, uuid: str) -> None:
        self._initials = (name[:2] or "?").upper()
        digest = hashlib.sha1(uuid.encode("utf-8")).digest()
        self._seed = digest[0]
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - API de Qt
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Tonos azules para mantener la identidad visual del launcher.
        hue = 205 + (self._seed % 40)
        top = QColor.fromHsv(hue, 150, 230)
        bottom = QColor.fromHsv((hue + 25) % 360, 190, 165)

        radius = self._size * 0.30
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(0, 0, self._size, self._size), radius, radius)
        gradient = QLinearGradient(0, 0, self._size, self._size)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor(255, 255, 255, 48), 1))
        painter.drawRoundedRect(
            QRectF(0.5, 0.5, self._size - 1, self._size - 1),
            radius, radius)

        font = QFont("Segoe UI", int(self._size * 0.34), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 225))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                         self._initials)
        painter.end()


class ConsoleView(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setMaximumBlockCount(2500)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setPlaceholderText(
            "El registro de descargas y del juego aparecerá aquí.")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def append(self, text: str) -> None:
        self.appendPlainText(text)


class _VersionPopup(QFrame):
    """Panel desplegable del selector de versiones.

    Muestra las versiones en un arbol agrupado por familia (1.12.x,
    26.x...) y, dentro, por version base: cada perfil OptiFine/Forge
    cuelga de su version madre. QTreeWidget solo pinta las filas
    visibles, asi que el scroll no renderiza la lista completa.
    """

    picked = pyqtSignal(str)

    _ROLE_ID = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("versionPopup")
        self.setFixedSize(430, 470)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filtrar versiones…")
        self.search.setClearButtonEnabled(True)
        layout.addWidget(self.search)

        self.tree = QTreeWidget()
        self.tree.setObjectName("versionTree")
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(False)
        layout.addWidget(self.tree, 1)

        self._entries: list[dict] = []
        self._selected = ""

        self.search.textChanged.connect(self._apply_filter)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemActivated.connect(self._on_item_clicked)

    # ------------------------------------------------------------ datos
    def set_entries(self, entries: list[dict], selected: str = "") -> None:
        self._entries = list(entries)
        self._selected = selected
        self._rebuild()
        self._apply_filter(self.search.text())

    def set_selected(self, version_id: str) -> None:
        self._selected = version_id
        target = self._find_item(self.tree.invisibleRootItem(),
                                 version_id)
        if target is not None:
            self._expand_to(target)
            self.tree.setCurrentItem(target)
            self.tree.scrollToItem(target)

    @staticmethod
    def _base_of(entry: dict) -> str:
        vid = entry.get("id", "")
        base = entry.get("base")
        if base:
            return base
        if entry.get("local"):
            payload = load_version_profile(vid) or {}
            return payload.get("inheritsFrom") or vid
        return vid

    def _group(self) -> dict:
        families: dict[str, dict] = {}
        for entry in self._entries:
            vid = entry.get("id", "")
            if not vid:
                continue
            base = self._base_of(entry)
            key = parse_version_key(base)
            label = version_family_label(base)
            family = families.setdefault(label, {"key": key, "bases": {}})
            node = family["bases"].setdefault(
                base, {"entry": None, "children": []})
            if base == vid:
                node["entry"] = entry
            else:
                node["children"].append(entry)
        return families

    @staticmethod
    def _kind_of(vid: str, base_id: str) -> str:
        lower = vid.lower()
        if "optifine" in lower:
            return "OptiFine"
        if "forge" in lower:
            return "Forge"
        if vid != base_id:
            return "perfil"
        return ""

    def _display_text(self, vid: str, base_id: str) -> str:
        label = vid
        if vid != base_id and vid.startswith(base_id + "-"):
            label = vid[len(base_id) + 1:]
        label = label.replace("_", " ")
        kind = self._kind_of(vid, base_id)
        return f"{label}   ·   {kind}" if kind else label

    def _version_item(self, vid: str, entry: dict | None,
                      base_id: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem([self._display_text(vid, base_id)])
        item.setData(0, self._ROLE_ID, vid)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled
                      | Qt.ItemFlag.ItemIsSelectable)
        if entry is not None and entry.get("local"):
            item.setForeground(0, QColor(theme.COLORS["TEXT_DIM"]))
        return item

    def _rebuild(self) -> None:
        self.tree.clear()
        for label, family in sorted(
                self._group().items(),
                key=lambda item: item[1]["key"], reverse=True):
            total = sum((1 if node["entry"] else 0) + len(node["children"])
                        for node in family["bases"].values())
            fam_item = QTreeWidgetItem([f"{label}   ({total})"])
            fam_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font = fam_item.font(0)
            font.setBold(True)
            fam_item.setFont(0, font)
            self.tree.addTopLevelItem(fam_item)

            bases = sorted(family["bases"].items(),
                           key=lambda item: parse_version_key(item[0]),
                           reverse=True)
            for base_id, node in bases:
                base_item = self._version_item(base_id, node["entry"],
                                               base_id)
                if node["entry"] is None:
                    # La version madre no esta en la lista: rama sin selector.
                    base_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    base_item.setData(0, self._ROLE_ID, None)
                    base_item.setText(
                        0, f"{base_id}   ·   version base no listada")
                fam_item.addChild(base_item)

                children = sorted(
                    node["children"],
                    key=lambda e: (parse_version_key(e.get("id", "")),
                                   e.get("id", "")),
                    reverse=True)
                for child in children:
                    base_item.addChild(self._version_item(
                        child["id"], child, base_id))
        self._restore_expansion()
        self._highlight()

    # -------------------------------------------------------- expansion
    def _find_item(self, parent: QTreeWidgetItem,
                   version_id: str) -> QTreeWidgetItem | None:
        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.data(0, self._ROLE_ID) == version_id:
                return item
            found = self._find_item(item, version_id)
            if found is not None:
                return found
        return None

    def _expand_to(self, item: QTreeWidgetItem) -> None:
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()

    def _restore_expansion(self) -> None:
        """Colapsa todas las familias salvo la que contiene la eleccion."""
        root = self.tree.invisibleRootItem()
        self._set_hidden_recursive(root, False)
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setExpanded(False)
        if self._selected:
            target = self._find_item(root, self._selected)
            if target is not None:
                self._expand_to(target)

    def _highlight(self) -> None:
        if not self._selected:
            return
        target = self._find_item(self.tree.invisibleRootItem(),
                                 self._selected)
        if target is not None:
            self.tree.setCurrentItem(target)

    # ----------------------------------------------------------- filtro
    def _apply_filter(self, text: str) -> None:
        query = text.strip().lower()
        if not query:
            self._restore_expansion()
            return
        for i in range(self.tree.topLevelItemCount()):
            family = self.tree.topLevelItem(i)
            visible = self._filter_node(family, query)
            family.setHidden(not visible)
            if visible:
                family.setExpanded(True)

    def _filter_node(self, item: QTreeWidgetItem, query: str) -> bool:
        vid = item.data(0, self._ROLE_ID)
        own = bool(vid and query in str(vid).lower())
        own = own or query in item.text(0).lower()
        child_visible = False
        for i in range(item.childCount()):
            if self._filter_node(item.child(i), query):
                child_visible = True
        visible = own or child_visible
        item.setHidden(not visible)
        return visible

    def _set_hidden_recursive(self, item: QTreeWidgetItem,
                              hidden: bool) -> None:
        item.setHidden(hidden)
        for i in range(item.childCount()):
            self._set_hidden_recursive(item.child(i), hidden)

    # ----------------------------------------------------------- senales
    def _on_item_clicked(self, item: QTreeWidgetItem,
                         column: int) -> None:  # noqa: ARG002
        vid = item.data(0, self._ROLE_ID)
        if vid:
            self.picked.emit(str(vid))
        else:
            item.setExpanded(not item.isExpanded())


class VersionPicker(QToolButton):
    """Boton que abre el arbol de versiones agrupadas por familia.

    Sustituto del QComboBox: mismo sitio en la UI, pero el desplegable
    agrupa cada perfil bajo su version madre y solo renderiza lo visible.
    """

    selectionChanged = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("versionPicker")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(34)
        self.setToolTip("Elegir la version de Minecraft")

        self._entries: list[dict] = []
        self._selected = ""
        self._placeholder = "Seleccionar versión…"
        # True cuando el arbol del popup refleja _entries: evita
        # reconstruir ~900 items en cada apertura del desplegable.
        self._popup_synced = False

        self._popup = _VersionPopup(self)
        self._popup.picked.connect(self._on_picked)
        self.clicked.connect(self._show_popup)
        self._refresh_text()

    # ------------------------------------------------------------ API
    def set_entries(self, entries: list[dict]) -> None:
        self._entries = list(entries)
        ids = {entry.get("id") for entry in entries}
        if self._selected not in ids:
            self._selected = ""
        self._popup_synced = False
        self._refresh_text()

    def select(self, version_id: str) -> None:
        """Seleccion programatica: no emite selectionChanged."""
        self._selected = version_id
        self._popup.set_selected(version_id)
        self._refresh_text()

    def ensure_entry(self, version_id: str) -> None:
        """Agrega un perfil local que el manifiesto no lista (Jugar)."""
        if any(entry.get("id") == version_id for entry in self._entries):
            return
        payload = load_version_profile(version_id) or {}
        base = payload.get("inheritsFrom") or version_id
        self._entries.append({"id": version_id, "type": "local",
                              "local": True, "base": base})
        self._popup.set_entries(self._entries, self._selected)
        self._popup_synced = True

    def current_id(self) -> str:
        return self._selected

    def count(self) -> int:
        return len(self._entries)

    def set_placeholder(self, text: str) -> None:
        self._placeholder = text
        if not self._selected:
            self._refresh_text()

    # ----------------------------------------------------------- internos
    def _show_popup(self) -> None:
        if not self.isEnabled() or self.count() == 0:
            return
        if self._popup_synced:
            # Las entradas no cambiaron: basta resaltar la eleccion.
            self._popup.set_selected(self._selected)
        else:
            self._popup.set_entries(self._entries, self._selected)
            self._popup_synced = True
        pos = self.mapToGlobal(self.rect().bottomLeft())
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            # El popup nunca debe salirse del area visible.
            size = QSize(min(430, area.width() - 16),
                         min(470, area.height() - 16))
            if self._popup.size() != size:
                self._popup.setFixedSize(size)
            popup_h = self._popup.height()
            if pos.y() + popup_h > area.bottom():
                # Sin sitio debajo: abrir hacia arriba del boton.
                pos = self.mapToGlobal(self.rect().topLeft())
                pos = pos - QPoint(0, popup_h)
            pos.setX(max(area.left(),
                         min(pos.x(), area.right() - self._popup.width())))
            pos.setY(max(area.top(), min(pos.y(),
                                        area.bottom() - popup_h)))
        self._popup.move(pos)
        self._popup.show()
        self._popup.raise_()
        self._popup.activateWindow()
        self._popup.search.setFocus()

    def _refresh_text(self) -> None:
        label = self._selected or self._placeholder
        self.setText(f"{label}   ▾")

    def _on_picked(self, version_id: str) -> None:
        self._popup.hide()
        if version_id == self._selected:
            return
        self._selected = version_id
        self._popup.set_selected(version_id)
        self._refresh_text()
        self.selectionChanged.emit(version_id)
