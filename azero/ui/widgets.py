"""Widgets reutilizables de la interfaz."""

from __future__ import annotations

import hashlib
from typing import Callable

from PyQt6.QtCore import QRectF, Qt, QUrl
from PyQt6.QtGui import (QColor, QDesktopServices, QFont, QLinearGradient,
                         QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                             QPlainTextEdit, QPushButton, QScrollArea,
                             QSizePolicy, QTableWidget, QTableWidgetItem,
                             QVBoxLayout, QWidget)

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
    layout.setContentsMargins(4, 5, 4, 5)
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

        self._holder = QWidget()
        self._holder.setObjectName("page")
        holder_layout = QHBoxLayout(self._holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(0)

        self.content = QWidget()
        self.content.setObjectName("page")
        self.content.setMaximumWidth(theme.CONTENT_MAX_WIDTH)
        self.body = QVBoxLayout(self.content)
        self.body.setContentsMargins(theme.PAGE_MARGIN, theme.PAGE_MARGIN,
                                     theme.PAGE_MARGIN, theme.PAGE_MARGIN)
        self.body.setSpacing(theme.PAGE_SPACING)

        holder_layout.addStretch(1)
        holder_layout.addWidget(self.content, 1)
        holder_layout.addStretch(1)
        self.scroll.setWidget(self._holder)
        outer.addWidget(self.scroll)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)


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
            "El registro de descargas y del juego aparecera aqui.")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def append(self, text: str) -> None:
        self.appendPlainText(text)
