"""Genera los recursos de marca de AZeroCraft.

Salida:
    assets/azero.ico          icono multiresolucion para exe e instalador
    assets/azero.png          marca 256 px para README/docs
    assets/banner.png         banner horizontal de README
    assets/wizard.bmp         panel ampliado del asistente de Inno Setup
    assets/wizard-small.bmp   icono pequeno del asistente

Uso: python packaging/make_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "assets"
ICON_PATH = ASSETS / "azero.ico"
PNG_PATH = ASSETS / "azero.png"
BANNER_PATH = ASSETS / "banner.png"
WIZARD_PATH = ASSETS / "wizard.bmp"
WIZARD_SMALL_PATH = ASSETS / "wizard-small.bmp"


def _save_bmp(pixmap, path: Path) -> None:
    """BMP opaco de 24 bits, el formato mas compatible con Inno Setup."""
    from PyQt6.QtGui import QImage
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    image.save(str(path), "BMP")


def main() -> int:
    from PyQt6.QtCore import QBuffer, QIODevice
    from PyQt6.QtGui import QImage
    from PyQt6.QtWidgets import QApplication

    from azero.branding import (SIZES, banner_pixmap, brand_pixmap,
                                wizard_pixmap, wizard_small_pixmap)

    app = QApplication.instance() or QApplication([])
    ASSETS.mkdir(parents=True, exist_ok=True)

    images: list[QImage] = []
    for size in SIZES:
        images.append(brand_pixmap(size).toImage())

    # QIcon no escribe .ico de forma fiable; construimos el contenedor ICO
    # manualmente con los PNG codificados por Qt.
    pngs = []
    for size, image in zip(SIZES, images):
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

    ICON_PATH.write_bytes(header + directory + data)
    brand_pixmap(256).save(str(PNG_PATH), "PNG")
    banner_pixmap().save(str(BANNER_PATH), "PNG")
    _save_bmp(wizard_pixmap(), WIZARD_PATH)
    _save_bmp(wizard_small_pixmap(), WIZARD_SMALL_PATH)

    print(f"Icono generado: {ICON_PATH} ({ICON_PATH.stat().st_size} bytes)")
    print(f"PNG generado: {PNG_PATH} ({PNG_PATH.stat().st_size} bytes)")
    print(f"Banner generado: {BANNER_PATH} ({BANNER_PATH.stat().st_size} bytes)")
    print(f"Wizard generado: {WIZARD_PATH} ({WIZARD_PATH.stat().st_size} bytes)")
    print(f"Wizard small generado: {WIZARD_SMALL_PATH} "
          f"({WIZARD_SMALL_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
