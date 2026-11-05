"""Genera assets/azero.ico con el mismo logo que usa la UI.

Uso: python packaging/make_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ICON_PATH = ROOT / "assets" / "azero.ico"


def main() -> int:
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PyQt6.QtCore import QBuffer, QIODevice, QRectF, Qt
    from PyQt6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPixmap
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    sizes = (16, 24, 32, 48, 64, 128, 256)
    images: list[QImage] = []
    for size in sizes:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, size, size), size * 0.24, size * 0.24)
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0.0, QColor("#4BF0B2"))
        gradient.setColorAt(1.0, QColor("#1FAE86"))
        painter.fillPath(path, gradient)
        font = QFont("Segoe UI", max(6, int(size * 0.46)), QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#062018"))
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "A")
        painter.end()
        images.append(pixmap.toImage())

    # QIcon no escribe .ico multiplataforma de forma fiable; construimos el
    # contenedor ICO manualmente con los PNG codificados por Qt.
    pngs = []
    for size, image in zip(sizes, images):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.convertToFormat(QImage.Format.Format_ARGB32).save(buffer, "PNG")
        pngs.append((size, bytes(buffer.data())))

    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    directory = b""
    data = b""
    for size, png in pngs:
        width = 0 if size >= 256 else size
        directory += struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32,
                                 len(png), offset)
        data += png
        offset += len(png)

    ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    ICON_PATH.write_bytes(header + directory + data)
    print(f"Icono generado: {ICON_PATH} ({ICON_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
