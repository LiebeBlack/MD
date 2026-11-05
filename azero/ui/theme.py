"""Tema visual: paleta, iconos generados y hoja de estilos."""

from __future__ import annotations

from pathlib import Path
from string import Template

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)
from PyQt6.QtWidgets import QApplication

from .. import paths

COLORS = {
    "BG": "#0A0D13",
    "SURFACE": "#111722",
    "SURFACE_ALT": "#161E2C",
    "SURFACE_HOVER": "#1C2636",
    "BORDER": "#232D3F",
    "BORDER_SOFT": "#1B2432",
    "TEXT": "#E7EEF9",
    "TEXT_DIM": "#93A1B7",
    "TEXT_FAINT": "#5F6C81",
    "ACCENT": "#3DE0A0",
    "ACCENT_DIM": "#2BB57F",
    "ACCENT_TEXT": "#062018",
    "DANGER": "#FF6B6B",
    "WARN": "#F2C14E",
}


def _ui_assets_dir() -> Path:
    target = paths.CACHE_DIR / "ui"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _draw_chevron(path: Path, color: str) -> None:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)])
    painter.end()
    pixmap.save(str(path))


def _draw_check(path: Path, color: str) -> None:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 3.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([QPointF(6, 12.5), QPointF(10.5, 17), QPointF(18, 8)])
    painter.end()
    pixmap.save(str(path))


def generate_assets() -> dict[str, str]:
    folder = _ui_assets_dir()
    chevron = folder / "chevron.png"
    check = folder / "check.png"
    _draw_chevron(chevron, COLORS["TEXT_DIM"])
    _draw_check(check, COLORS["ACCENT_TEXT"])
    return {
        "chevron": chevron.as_posix(),
        "check": check.as_posix(),
    }


def app_icon() -> QIcon:
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(4, 4, 120, 120), 30, 30)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0.0, QColor("#4BF0B2"))
    gradient.setColorAt(1.0, QColor("#1FAE86"))
    painter.fillPath(path, gradient)

    font = QFont("Segoe UI", 58, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(COLORS["ACCENT_TEXT"]))
    painter.drawText(QRectF(0, 0, 128, 128), Qt.AlignmentFlag.AlignCenter, "A")
    painter.end()
    return QIcon(pixmap)


QSS = Template("""
* {
    outline: none;
}
QWidget {
    color: $TEXT;
    font-family: "Segoe UI", "Inter", "Noto Sans", sans-serif;
    font-size: 10pt;
}
QWidget#root {
    background-color: $BG;
}
QMainWindow {
    background-color: $BG;
}
QFrame#card {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 12px;
}
QFrame#softPanel {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
}
QLabel {
    background: transparent;
}
QLabel#brandTitle {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 20pt;
    font-weight: 800;
    letter-spacing: 0.5px;
}
QLabel#brandAccent {
    color: $ACCENT;
}
QLabel#sectionLabel {
    color: $TEXT_FAINT;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.4px;
}
QLabel#muted {
    color: $TEXT_DIM;
    font-size: 9pt;
}
QLabel#faint {
    color: $TEXT_FAINT;
    font-size: 8pt;
}
QLabel#mono {
    color: $TEXT_FAINT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
}
QLabel#valueLabel {
    color: $TEXT;
    font-weight: 700;
}
QLabel#pill {
    background-color: rgba(61, 224, 160, 0.10);
    color: $ACCENT;
    border: 1px solid rgba(61, 224, 160, 0.28);
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QLabel#pillDim {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 8pt;
}
QLabel#statusLabel {
    color: $TEXT_DIM;
    font-size: 9pt;
}
QLabel#statusError {
    color: $DANGER;
    font-size: 9pt;
}
QLabel#statusOk {
    color: $ACCENT;
    font-size: 9pt;
}

QLineEdit {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: $ACCENT_DIM;
    selection-color: $ACCENT_TEXT;
}
QLineEdit:hover {
    border-color: #2C3A50;
}
QLineEdit:focus {
    border-color: $ACCENT;
    background-color: #121A26;
}
QLineEdit#nameEdit {
    font-size: 12pt;
    font-weight: 700;
    padding: 4px 8px;
    background: transparent;
    border: 1px solid transparent;
}
QLineEdit#nameEdit:hover, QLineEdit#nameEdit:focus {
    background-color: $SURFACE_ALT;
    border-color: $BORDER;
}

QComboBox {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 18px;
}
QComboBox:hover {
    border-color: #2C3A50;
}
QComboBox:focus {
    border-color: $ACCENT;
}
QComboBox::drop-down {
    border: none;
    width: 28px;
}
QComboBox::down-arrow {
    image: url("$CHEVRON");
    width: 14px;
    height: 14px;
}
QComboBox QAbstractItemView {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 10px;
    padding: 6px;
    selection-background-color: rgba(61, 224, 160, 0.16);
    selection-color: $TEXT;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 7px 8px;
    border-radius: 6px;
    min-height: 20px;
}

QPushButton {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 7px 13px;
    color: $TEXT;
}
QPushButton:hover {
    background-color: $SURFACE_HOVER;
    border-color: #2E3B51;
}
QPushButton:pressed {
    background-color: #0F1622;
}
QPushButton:disabled {
    color: $TEXT_FAINT;
    background-color: #10161F;
    border-color: #1A2230;
}
QPushButton#playButton {
    background-color: $ACCENT;
    border: none;
    border-radius: 10px;
    color: $ACCENT_TEXT;
    font-size: 12pt;
    font-weight: 800;
    letter-spacing: 1.0px;
    padding: 12px 16px;
}
QPushButton#playButton:hover {
    background-color: #58F0B6;
}
QPushButton#playButton:pressed {
    background-color: $ACCENT_DIM;
}
QPushButton#playButton:disabled {
    background-color: #1C2A2A;
    color: #4C6B60;
}
QPushButton#playButton[busy="true"] {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
}
QPushButton#playButton[busy="true"]:hover {
    color: $TEXT;
    border-color: #3A4A63;
}
QPushButton#ghostButton {
    background: transparent;
    border: 1px solid transparent;
    color: $TEXT_DIM;
    padding: 6px 10px;
}
QPushButton#ghostButton:hover {
    color: $TEXT;
    background-color: $SURFACE_ALT;
}
QPushButton#accentGhost {
    background: transparent;
    border: 1px solid rgba(61, 224, 160, 0.35);
    color: $ACCENT;
    padding: 6px 12px;
    font-size: 9pt;
}
QPushButton#accentGhost:hover {
    background-color: rgba(61, 224, 160, 0.10);
}
QPushButton#iconButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 6px;
    font-size: 13pt;
    color: $TEXT_DIM;
}
QPushButton#iconButton:hover {
    background-color: $SURFACE_ALT;
    color: $TEXT;
    border-color: $BORDER;
}

QCheckBox {
    color: $TEXT_DIM;
    spacing: 10px;
    font-size: 9pt;
}
QCheckBox:hover {
    color: $TEXT;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid $BORDER;
    background-color: $SURFACE_ALT;
}
QCheckBox::indicator:hover {
    border-color: #34435C;
}
QCheckBox::indicator:checked {
    background-color: $ACCENT;
    border-color: $ACCENT;
    image: url("$CHECK");
}

QSlider::groove:horizontal {
    height: 5px;
    background: #1D2636;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: $ACCENT;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #E9FFF7;
    width: 15px;
    height: 15px;
    margin: -6px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #FFFFFF;
}

QPlainTextEdit#console {
    background-color: #0A0F17;
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
    color: #B9C6D8;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8.5pt;
    selection-background-color: #1F4C3C;
    padding: 8px;
}

QProgressBar {
    background-color: #131A25;
    border: 1px solid $BORDER_SOFT;
    border-radius: 5px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: $ACCENT;
    border-radius: 4px;
}

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: #2A3548;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #384862;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QDialog {
    background-color: $BG;
}
QToolTip {
    background-color: $SURFACE_ALT;
    color: $TEXT;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 5px 8px;
}
QMessageBox {
    background-color: $SURFACE;
}
QFrame#divider {
    background-color: $BORDER_SOFT;
    max-height: 1px;
    border: none;
}
""")


def build_stylesheet() -> str:
    assets = generate_assets()
    return QSS.substitute(**COLORS, CHEVRON=assets["chevron"], CHECK=assets["check"])


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
