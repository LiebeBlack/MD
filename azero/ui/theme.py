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
    "BG": "#0B0E14",
    "SURFACE": "#11161F",
    "SURFACE_ALT": "#171E2A",
    "SURFACE_HOVER": "#1D2634",
    "BORDER": "#26303F",
    "BORDER_SOFT": "#1C2431",
    "TEXT": "#E8EEF7",
    "TEXT_DIM": "#94A2B8",
    "TEXT_FAINT": "#5E6B80",
    "ACCENT": "#3DDC97",
    "ACCENT_DIM": "#2BAE77",
    "ACCENT_TEXT": "#052015",
    "DANGER": "#FF7070",
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
    font-size: 9.5pt;
}
QWidget#root {
    background-color: $BG;
}
QMainWindow {
    background-color: $BG;
}
QStackedWidget, QScrollArea {
    background: transparent;
}
QFrame#card {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 9px;
}
QFrame#softPanel {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_SOFT;
    border-radius: 7px;
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
    font-size: 8.5pt;
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
    background-color: rgba(61, 220, 151, 0.10);
    color: $ACCENT;
    border: 1px solid rgba(61, 220, 151, 0.28);
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QLabel#pillDim {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 8pt;
}
QLabel#statusLabel {
    color: $TEXT_DIM;
    font-size: 8.5pt;
}
QLabel#statusError {
    color: $DANGER;
    font-size: 8.5pt;
}
QLabel#statusOk {
    color: $ACCENT;
    font-size: 8.5pt;
}

QLineEdit {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 7px;
    padding: 5px 9px;
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
    border-radius: 7px;
    padding: 4px 9px;
    min-height: 16px;
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
    border-radius: 8px;
    padding: 4px;
    selection-background-color: rgba(61, 220, 151, 0.14);
    selection-color: $TEXT;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 5px 8px;
    border-radius: 5px;
    min-height: 18px;
}

QPushButton {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 7px;
    padding: 5px 11px;
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
    border-radius: 8px;
    color: $ACCENT_TEXT;
    font-size: 12pt;
    font-weight: 800;
    letter-spacing: 1.0px;
    padding: 9px 14px;
}
QPushButton#playButton:hover {
    background-color: #6FE7B8;
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
    padding: 4px 9px;
}
QPushButton#ghostButton:hover {
    color: $TEXT;
    background-color: $SURFACE_ALT;
}
QPushButton#accentGhost {
    background: transparent;
    border: 1px solid rgba(61, 220, 151, 0.35);
    color: $ACCENT;
    padding: 4px 11px;
    font-size: 9pt;
}
QPushButton#accentGhost:hover {
    background-color: rgba(61, 220, 151, 0.10);
}
QPushButton#iconButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 5px;
    font-size: 12pt;
    color: $TEXT_DIM;
}
QPushButton#iconButton:hover {
    background-color: $SURFACE_ALT;
    color: $TEXT;
    border-color: $BORDER;
}

QSpinBox {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 7px;
    padding: 4px 9px;
    min-height: 16px;
    color: $TEXT;
}
QSpinBox:hover {
    border-color: #2C3A50;
}
QSpinBox:focus {
    border-color: $ACCENT;
    background-color: #121A26;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 20px;
    border: none;
    background: transparent;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: $SURFACE_HOVER;
    border-radius: 4px;
}
QCheckBox {
    color: $TEXT_DIM;
    spacing: 8px;
    font-size: 8.5pt;
}
QCheckBox:hover {
    color: $TEXT;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 4px;
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
    height: 4px;
    background: #1D2636;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: $ACCENT;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E9FFF7;
    width: 13px;
    height: 13px;
    margin: -5px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #FFFFFF;
}

QPlainTextEdit#console {
    background-color: #0A0F17;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
    color: #B9C6D8;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
    selection-background-color: #1F4C3C;
    padding: 6px;
}

QProgressBar {
    background-color: #131A25;
    border: 1px solid $BORDER_SOFT;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: $ACCENT;
    border-radius: 3px;
}

QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 4px 0;
}
QScrollBar::handle:vertical {
    background: #2A3548;
    border-radius: 4px;
    min-height: 24px;
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

/* ---- navegacion lateral (estilo navegador) ---- */
QWidget#sidebar {
    background-color: #0D1119;
    border-right: 1px solid $BORDER_SOFT;
}
QLabel#navTitle {
    color: $TEXT_FAINT;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.4px;
    padding: 3px 10px;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: $TEXT_DIM;
    text-align: left;
    padding: 7px 12px;
    font-size: 9.5pt;
    font-weight: 600;
    min-height: 16px;
}
QPushButton#navButton:hover {
    background-color: $SURFACE_HOVER;
    color: $TEXT;
}
QPushButton#navButton[active="true"] {
    background-color: rgba(61, 220, 151, 0.10);
    border-color: rgba(61, 220, 151, 0.26);
    color: $ACCENT;
}
QLabel#navBadge {
    color: $TEXT_FAINT;
    font-size: 8pt;
}

/* ---- paginas y tablas ---- */
QWidget#page {
    background: transparent;
}
QLabel#pageTitle {
    color: $TEXT;
    font-size: 15pt;
    font-weight: 800;
}
QLabel#pageSubtitle {
    color: $TEXT_DIM;
    font-size: 8.5pt;
}
QTableWidget, QListWidget {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
    gridline-color: $BORDER_SOFT;
    color: $TEXT;
    font-size: 8.5pt;
    selection-background-color: rgba(61, 220, 151, 0.14);
    selection-color: $TEXT;
    outline: none;
}
QTableWidget::item, QListWidget::item {
    padding: 3px 8px;
    border: none;
}
QTableWidget::item:hover, QListWidget::item:hover {
    background-color: $SURFACE_HOVER;
}
QHeaderView::section {
    background-color: $SURFACE_ALT;
    color: $TEXT_FAINT;
    border: none;
    border-bottom: 1px solid $BORDER;
    padding: 5px 10px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QTableCornerButton::section {
    background-color: $SURFACE_ALT;
    border: none;
}
QListWidget::item:selected {
    background-color: rgba(61, 220, 151, 0.14);
    color: $TEXT;
}
QPushButton#dangerButton {
    background: transparent;
    border: 1px solid rgba(255, 107, 107, 0.4);
    color: $DANGER;
    padding: 4px 11px;
}
QPushButton#dangerButton:hover {
    background-color: rgba(255, 107, 107, 0.10);
}
QPushButton#primaryButton {
    background-color: $ACCENT;
    border: none;
    border-radius: 7px;
    color: $ACCENT_TEXT;
    font-weight: 700;
    padding: 6px 14px;
}
QPushButton#primaryButton:hover {
    background-color: #6FE7B8;
}
QPushButton#primaryButton:disabled {
    background-color: #1C2A2A;
    color: #4C6B60;
}
QFrame#statCard {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
}
QLabel#statValue {
    color: $TEXT;
    font-size: 13pt;
    font-weight: 800;
}
QLabel#statCaption {
    color: $TEXT_FAINT;
    font-size: 8pt;
    letter-spacing: 0.6px;
}
QScrollArea {
    background: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
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
