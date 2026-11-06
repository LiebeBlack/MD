"""Identidad visual de AZeroCraft: marca vectorial y recursos de marca.

El logo se dibuja con QPainter, sin fuentes ni imagenes externas. Asi el
.ico generado por el build es identico al que usa la aplicacion en runtime.
"""

from __future__ import annotations

from functools import lru_cache

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QIcon,
                         QLinearGradient, QPainter, QPainterPath, QPen,
                         QPixmap)

from . import APP_VERSION

SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)

_TOP = "#5AA7F0"
_MID = "#2F7BD6"
_BOTTOM = "#0F55A8"
_MARK = "#FFFFFF"


def brand_mark(painter: QPainter, color: QColor | None = None,
               stroke: float = 13.5) -> None:
    """Dibuja la A geometrica en el sistema de coordenadas de 128 px."""
    painter.setPen(QPen(color or QColor(_MARK), stroke,
                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPolyline([QPointF(37, 100), QPointF(64, 28),
                          QPointF(91, 100)])
    painter.drawLine(QPointF(48, 73), QPointF(80, 73))


def _background(painter: QPainter, width: int, height: int,
                step: int = 22) -> None:
    """Fondo azul con trama diagonal, comun al wizard y al banner."""
    gradient = QLinearGradient(0, 0, width, height)
    gradient.setColorAt(0.0, QColor("#0A2F58"))
    gradient.setColorAt(0.55, QColor("#0F5CAD"))
    gradient.setColorAt(1.0, QColor("#0A2342"))
    painter.fillRect(QRectF(0, 0, width, height), gradient)
    painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
    for x in range(-height, width + height, step):
        painter.drawLine(x, 0, x + height, height)


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

    shine = QLinearGradient(0, 0, 0, 128)
    shine.setColorAt(0.0, QColor(255, 255, 255, 56))
    shine.setColorAt(0.55, QColor(255, 255, 255, 0))
    painter.fillPath(tile, shine)

    painter.setPen(QPen(QColor(255, 255, 255, 58), 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(5.5, 5.5, 117, 117), 25.5, 25.5)
    brand_mark(painter)
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


def wizard_pixmap(width: int = 192, height: int = 386) -> QPixmap:
    """Panel vertical ampliado del asistente de Inno Setup."""
    width = max(164, int(width))
    height = max(314, int(height))
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#0A2F58"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _background(painter, width, height)

    # Marca de agua grande al pie.
    painter.save()
    painter.setOpacity(0.10)
    painter.translate(-20, 208)
    painter.scale(1.7, 1.7)
    brand_mark(painter, QColor("#FFFFFF"), 24)
    painter.restore()

    # Tarjeta blanca con el icono, mas grande que en el wizard original.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 236))
    painter.drawRoundedRect(QRectF(46, 28, 100, 100), 24, 24)
    painter.drawPixmap(54, 36, brand_pixmap(84))

    if QFontDatabase.families():
        label = QFont("Segoe UI")
        label.setPixelSize(9)
        label.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.6)
        painter.setFont(label)
        painter.setPen(QColor("#A9D2F5"))
        painter.drawText(QRectF(0, 136, width, 14),
                         Qt.AlignmentFlag.AlignCenter, "INSTALADOR")

        painter.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(0, 148, width, 28),
                         Qt.AlignmentFlag.AlignCenter, "AZeroCraft")

        tagline = QFont("Segoe UI", 7)
        tagline.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(tagline)
        painter.setPen(QColor("#A9D2F5"))
        painter.drawText(QRectF(0, 180, width, 14),
                         Qt.AlignmentFlag.AlignCenter,
                         "LAUNCHER 1.8 – 1.15.2")

        footer = QFont("Segoe UI")
        footer.setPixelSize(9)
        painter.setFont(footer)
        painter.setPen(QColor("#9CC7F0"))
        painter.drawText(QRectF(0, height - 30, width, 14),
                         Qt.AlignmentFlag.AlignCenter,
                         "github.com/LiebeBlack/MD")

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(124, 199, 255, 220))
    painter.drawRoundedRect(QRectF((width - 44) / 2, 200, 44, 3), 1.5, 1.5)
    painter.end()
    return pixmap


def banner_pixmap(width: int = 1200, height: int = 260) -> QPixmap:
    """Banner horizontal de marca para el README y la documentacion."""
    width = max(640, int(width))
    height = max(200, int(height))
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor("#0A2F58"))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    _background(painter, width, height, step=26)

    # A gigante como marca de agua a la derecha.
    painter.save()
    painter.setOpacity(0.09)
    painter.translate(width - 300, -4)
    painter.scale(2.6, 2.6)
    brand_mark(painter, QColor("#FFFFFF"), 26)
    painter.restore()

    # Tarjeta del icono.
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 236))
    painter.drawRoundedRect(QRectF(48, 64, 132, 132), 28, 28)
    painter.drawPixmap(60, 76, brand_pixmap(108))

    if QFontDatabase.families():
        label = QFont("Segoe UI", 7)
        label.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(label)
        painter.setPen(QColor("#A9D2F5"))
        painter.drawText(QRectF(210, 34, width - 520, 16),
                         Qt.AlignmentFlag.AlignLeft
                         | Qt.AlignmentFlag.AlignVCenter,
                         "MINECRAFT JAVA EDITION")

        painter.setFont(QFont("Segoe UI", 34, QFont.Weight.Bold))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(210, 52, width - 520, 58),
                         Qt.AlignmentFlag.AlignLeft
                         | Qt.AlignmentFlag.AlignVCenter,
                         "AZeroCraft Launcher")

        painter.setFont(QFont("Segoe UI", 10))
        painter.setPen(QColor("#C7E2FA"))
        painter.drawText(QRectF(210, 118, width - 520, 24),
                         Qt.AlignmentFlag.AlignLeft
                         | Qt.AlignmentFlag.AlignVCenter,
                         "Launcher de Minecraft Java Edition · "
                         "1.8 – 1.15.2 · Windows")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(124, 199, 255, 230))
        painter.drawRoundedRect(QRectF(210, 148, 64, 3), 1.5, 1.5)

        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#9CC7F0"))
        painter.drawText(QRectF(210, 176, width - 520, 18),
                         Qt.AlignmentFlag.AlignLeft
                         | Qt.AlignmentFlag.AlignVCenter,
                         f"github.com/LiebeBlack/MD · v{APP_VERSION}")

    painter.end()
    return pixmap
