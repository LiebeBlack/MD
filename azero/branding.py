"""Identidad visual de AZeroCraft: marca vectorial y recursos de instalacion.

El icono se dibuja con QPainter, sin fuentes ni imagenes externas. Asi el
.ico generado por el build es identico al que usa la aplicacion en runtime.
"""

from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QIcon,
                         QLinearGradient, QPainter, QPainterPath, QPen,
                         QPixmap)

SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)

_TOP = "#5AA7F0"
_MID = "#2F7BD6"
_BOTTOM = "#0F55A8"
_MARK = "#FFFFFF"


def _mark(painter: QPainter, color: QColor | None = None,
          stroke: float = 13.5) -> None:
    """Dibuja la A geometrica en el sistema de coordenadas de 128 px."""
    painter.setPen(QPen(color or QColor(_MARK), stroke,
                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolyline([QPointF(37, 100), QPointF(64, 28),
                          QPointF(91, 100)])
    painter.drawLine(QPointF(48, 73), QPointF(80, 73))


def brand_pixmap(size: int = 128) -> QPixmap:
    """Icono cuadrado de la marca, escalado sin perder nitidez."""
    size = max(16, int(size))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 128.0, size / 128.0)

    tile = QPainterPath()
    tile.addRoundedRect(QRectF(4, 4, 120, 120), 27, 27)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0.0, QColor(_TOP))
    gradient.setColorAt(0.52, QColor(_MID))
    gradient.setColorAt(1.0, QColor(_BOTTOM))
    painter.fillPath(tile, gradient)

    # Brillo superior sutil, sin depender de imagenes externas.
    shine = QLinearGradient(0, 0, 0, 128)
    shine.setColorAt(0.0, QColor(255, 255, 255, 56))
    shine.setColorAt(0.55, QColor(255, 255, 255, 0))
    painter.fillPath(tile, shine)

    painter.setPen(QPen(QColor(255, 255, 255, 58), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(5.5, 5.5, 117, 117), 25.5, 25.5)
    _mark(painter)
    painter.end()
    return pixmap


@lru_cache(maxsize=1)
def brand_icon() -> QIcon:
    """QIcon con todos los tamanos que usan Windows y Qt."""
    icon = QIcon()
    for size in SIZES:
        icon.addPixmap(brand_pixmap(size))
    return icon


def wizard_small_pixmap(size: int = 55) -> QPixmap:
    """Icono pequeno del asistente con fondo opaco para el BMP."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor("#FFFFFF"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap(0, 0, brand_pixmap(size))
    painter.end()
    return pixmap


def wizard_pixmap(width: int = 164, height: int = 314) -> QPixmap:
    """Panel vertical de marca para el asistente de Inno Setup."""
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#0A2F58"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    background = QLinearGradient(0, 0, width, height)
    background.setColorAt(0.0, QColor("#0A2F58"))
    background.setColorAt(0.55, QColor("#0F5CAD"))
    background.setColorAt(1.0, QColor("#0A2342"))
    painter.fillRect(QRectF(0, 0, width, height), background)

    # Trama diagonal muy sutil.
    painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
    for x in range(-height, width + height, 22):
        painter.drawLine(x, 0, x + height, height)

    # Marca de agua grande al pie.
    painter.save()
    painter.setOpacity(0.10)
    painter.translate(-14, 158)
    painter.scale(1.55, 1.55)
    _mark(painter, QColor("#FFFFFF"), 24)
    painter.restore()

    # Tarjeta blanca con el icono, separada del fondo azul.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 236))
    painter.drawRoundedRect(QRectF(42, 24, 80, 80), 20, 20)
    painter.drawPixmap(50, 32, brand_pixmap(64))

    # El texto solo se dibuja si el entorno tiene fuentes (Windows normal).
    if QFontDatabase.families():
        painter.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, 112, width, 24),
                         Qt.AlignmentFlag.AlignCenter, "AZeroCraft")

        small = QFont("Segoe UI", 6)
        small.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.4)
        painter.setFont(small)
        painter.setPen(QColor("#A9D2F5"))
        painter.drawText(QRectF(0, 134, width, 14),
                         Qt.AlignmentFlag.AlignCenter,
                         "LAUNCHER 1.8 – 1.15.2")

        footer = QFont("Segoe UI", 6)
        painter.setFont(footer)
        painter.setPen(QColor("#9CC7F0"))
        painter.drawText(QRectF(0, height - 28, width, 14),
                         Qt.AlignmentFlag.AlignCenter,
                         "github.com/LiebeBlack/MD")

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(124, 199, 255, 220))
    painter.drawRoundedRect(QRectF(64, 154, 36, 3), 1.5, 1.5)
    painter.end()
    return pixmap
