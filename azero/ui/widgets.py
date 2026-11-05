"""Widgets reutilizables de la interfaz."""

from __future__ import annotations

import hashlib

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PyQt6.QtWidgets import (QFrame, QLabel, QPlainTextEdit, QSizePolicy,
                             QVBoxLayout, QWidget)


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, margins: int = 11,
                 spacing: int = 8):
        super().__init__(parent)
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(margins, margins, margins, margins)
        self.body.setSpacing(spacing)


class Divider(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("divider")
        self.setFixedHeight(1)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


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
    return label


class Pill(QLabel):
    def __init__(self, text: str, dim: bool = False, parent: QWidget | None = None):
        super().__init__(text.upper(), parent)
        self.setObjectName("pillDim" if dim else "pill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


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

        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self._size, self._size),
                            self._size * 0.30, self._size * 0.30)
        gradient = QLinearGradient(0, 0, self._size, self._size)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, bottom)
        painter.fillPath(path, gradient)

        font = QFont("Segoe UI", int(self._size * 0.34), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(255, 255, 255, 225))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._initials)
        painter.end()


class ConsoleView(QPlainTextEdit):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("console")
        self.setReadOnly(True)
        self.setMaximumBlockCount(2500)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setPlaceholderText("El registro de descargas y del juego aparecera aqui.")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def append(self, text: str) -> None:
        self.appendPlainText(text)
