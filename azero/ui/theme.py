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
    "BG": "#07090E",
    "BG_ALT": "#0B0E15",
    "SURFACE": "#0E131C",
    "SURFACE_ALT": "#131A26",
    "SURFACE_HOVER": "#1A2334",
    "SURFACE_PRESSED": "#0D1420",
    "BORDER": "#27303F",
    "BORDER_SOFT": "#171E2B",
    "BORDER_STRONG": "#33405A",
    "TEXT": "#EDF2FA",
    "TEXT_DIM": "#8E9DB4",
    "TEXT_FAINT": "#5C6B84",
    "ACCENT": "#3DDC97",
    "ACCENT_HI": "#63E8B4",
    "ACCENT_DIM": "#2BAE77",
    "ACCENT_DEEP": "#1E9A70",
    "ACCENT_TEXT": "#052015",
    "ACCENT2": "#8B7CFF",
    "INFO": "#6CB8FF",
    "DANGER": "#FF7A7A",
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

/* ---- tarjetas y paneles ---- */
QFrame#card {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 13px;
}
QFrame#card:hover {
    border-color: #1D2635;
}
QFrame#softPanel {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_SOFT;
    border-radius: 9px;
}
QFrame#softPanel:hover {
    border-color: $BORDER;
}

/* ---- etiquetas ---- */
QLabel {
    background: transparent;
}
QLabel#brandTitle {
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 15pt;
    font-weight: 800;
    letter-spacing: 0.4px;
}
QLabel#brandAccent {
    color: $ACCENT;
}
QLabel#sectionLabel {
    color: $TEXT_FAINT;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.8px;
    padding-top: 2px;
}
QLabel#muted {
    color: $TEXT_DIM;
    font-size: 8.5pt;
    line-height: 1.35;
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
    background-color: rgba(61, 220, 151, 0.11);
    color: $ACCENT;
    border: 1px solid rgba(61, 220, 151, 0.30);
    border-radius: 9px;
    padding: 3px 10px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 0.9px;
}
QLabel#pillDim {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
    border-radius: 9px;
    padding: 3px 10px;
    font-size: 8pt;
}
QLabel#statusLabel {
    color: $TEXT_DIM;
    font-size: 8.5pt;
}
QLabel#statusError {
    color: $DANGER;
    font-size: 8.5pt;
    font-weight: 600;
}
QLabel#statusOk {
    color: $ACCENT;
    font-size: 8.5pt;
    font-weight: 600;
}

/* ---- campos de texto ---- */
QLineEdit {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: $ACCENT_DIM;
    selection-color: $ACCENT_TEXT;
}
QLineEdit:hover {
    border-color: $BORDER_STRONG;
    background-color: #16202F;
}
QLineEdit:focus {
    border-color: $ACCENT;
    background-color: #101828;
}
QLineEdit:disabled {
    color: $TEXT_FAINT;
    background-color: #0F1520;
}
QLineEdit#nameEdit {
    font-size: 12pt;
    font-weight: 700;
    padding: 4px 8px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
}
QLineEdit#nameEdit:hover, QLineEdit#nameEdit:focus {
    background-color: $SURFACE_ALT;
    border-color: $BORDER;
}

/* ---- combos ---- */
QComboBox {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 9px;
    padding: 6px 34px 6px 11px;
    min-height: 18px;
}
QComboBox:hover {
    border-color: $BORDER_STRONG;
    background-color: #16202F;
}
QComboBox:focus {
    border-color: $ACCENT;
    background-color: #101828;
}
QComboBox:disabled {
    color: $TEXT_FAINT;
    background-color: #0F1520;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: url("$CHEVRON");
    width: 14px;
    height: 14px;
}
QComboBox QAbstractItemView {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 9px;
    padding: 5px;
    selection-background-color: rgba(61, 220, 151, 0.15);
    selection-color: $TEXT;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 6px 9px;
    border-radius: 6px;
    min-height: 18px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: $SURFACE_HOVER;
}
QComboBox QAbstractItemView::item:selected {
    background-color: rgba(61, 220, 151, 0.15);
}

/* ---- botones ---- */
QAbstractButton:focus {
    border-color: $ACCENT_DIM;
}
QPushButton {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 6px 13px;
    color: $TEXT;
    font-weight: 600;
}
QPushButton:hover {
    background-color: $SURFACE_HOVER;
    border-color: $BORDER_STRONG;
}
QPushButton:pressed {
    background-color: $SURFACE_PRESSED;
    border-color: $BORDER;
}
QPushButton:disabled {
    color: $TEXT_FAINT;
    background-color: #0E141F;
    border-color: $BORDER_SOFT;
}
QPushButton#playButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #4BF0B2, stop:1 #25B57F);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 11px;
    color: $ACCENT_TEXT;
    font-size: 13pt;
    font-weight: 800;
    letter-spacing: 1.2px;
    padding: 11px 18px;
}
QPushButton#playButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #6FF2C4, stop:1 #35D493);
    border-color: rgba(255, 255, 255, 0.18);
}
QPushButton#playButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #2BBE8F, stop:1 #1E9A70);
}
QPushButton#playButton:disabled {
    background: #14201D;
    border-color: #1E2E2A;
    color: #47705F;
}
QPushButton#playButton[busy="true"] {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
}
QPushButton#playButton[busy="true"]:hover {
    color: $TEXT;
    border-color: $BORDER_STRONG;
}
QPushButton#ghostButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    color: $TEXT_DIM;
    padding: 5px 10px;
    font-weight: 600;
}
QPushButton#ghostButton:hover {
    color: $TEXT;
    background-color: $SURFACE_HOVER;
    border-color: $BORDER_SOFT;
}
QPushButton#ghostButton:pressed {
    background-color: $SURFACE_PRESSED;
}
QPushButton#ghostButton:disabled {
    color: $TEXT_FAINT;
    background: transparent;
    border-color: transparent;
}
QPushButton#accentGhost {
    background: rgba(61, 220, 151, 0.07);
    border: 1px solid rgba(61, 220, 151, 0.32);
    border-radius: 8px;
    color: $ACCENT;
    padding: 6px 13px;
    font-size: 9pt;
    font-weight: 700;
}
QPushButton#accentGhost:hover {
    background-color: rgba(61, 220, 151, 0.15);
    border-color: rgba(61, 220, 151, 0.50);
}
QPushButton#accentGhost:pressed {
    background-color: rgba(61, 220, 151, 0.22);
}
QPushButton#accentGhost:disabled {
    color: $TEXT_FAINT;
    background-color: #0E141F;
    border-color: $BORDER_SOFT;
}
QPushButton#iconButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 5px;
    font-size: 12pt;
    color: $TEXT_DIM;
}
QPushButton#iconButton:hover {
    background-color: $SURFACE_HOVER;
    color: $TEXT;
    border-color: $BORDER_SOFT;
}
QPushButton#iconButton:pressed {
    background-color: $SURFACE_PRESSED;
}
QPushButton#iconButton:disabled {
    color: $TEXT_FAINT;
}
QPushButton#dangerButton {
    background: transparent;
    border: 1px solid rgba(255, 122, 122, 0.35);
    border-radius: 8px;
    color: $DANGER;
    padding: 5px 12px;
    font-weight: 600;
}
QPushButton#dangerButton:hover {
    background-color: rgba(255, 122, 122, 0.12);
    border-color: rgba(255, 122, 122, 0.55);
}
QPushButton#dangerButton:pressed {
    background-color: rgba(255, 122, 122, 0.20);
}
QPushButton#dangerButton:disabled {
    color: #6E4A4A;
    border-color: rgba(255, 122, 122, 0.15);
}
QPushButton#primaryButton {
    background-color: $ACCENT;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    color: $ACCENT_TEXT;
    font-weight: 700;
    padding: 7px 15px;
}
QPushButton#primaryButton:hover {
    background-color: $ACCENT_HI;
    border-color: rgba(255, 255, 255, 0.22);
}
QPushButton#primaryButton:pressed {
    background-color: $ACCENT_DIM;
}
QPushButton#primaryButton:disabled {
    background-color: #14201D;
    border-color: #1E2E2A;
    color: #47705F;
}

/* ---- spin boxes ---- */
QSpinBox {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 5px 9px;
    min-height: 16px;
    color: $TEXT;
}
QSpinBox:hover {
    border-color: $BORDER_STRONG;
    background-color: #16202F;
}
QSpinBox:focus {
    border-color: $ACCENT;
    background-color: #101828;
}
QSpinBox:disabled {
    color: $TEXT_FAINT;
    background-color: #0F1520;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 22px;
    border: none;
    background: transparent;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: $SURFACE_HOVER;
    border-radius: 5px;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: $ACCENT_DIM;
}

/* ---- checks y sliders ---- */
QCheckBox {
    color: $TEXT_DIM;
    spacing: 9px;
    font-size: 8.5pt;
}
QCheckBox:hover {
    color: $TEXT;
}
QCheckBox:disabled {
    color: $TEXT_FAINT;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid $BORDER_STRONG;
    background-color: $SURFACE_ALT;
}
QCheckBox::indicator:hover {
    border-color: $ACCENT_DIM;
    background-color: #16202F;
}
QCheckBox::indicator:checked {
    background-color: $ACCENT;
    border-color: $ACCENT;
    image: url("$CHECK");
}
QCheckBox::indicator:checked:hover {
    background-color: $ACCENT_HI;
}
QCheckBox::indicator:disabled {
    background-color: #10151F;
    border-color: $BORDER_SOFT;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #1B2333;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 $ACCENT_DIM, stop:1 $ACCENT);
    border-radius: 3px;
}
QSlider::add-page:horizontal {
    background: #161F2E;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #F2FBF7;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 2px solid #0A0E15;
}
QSlider::handle:horizontal:hover {
    background: #FFFFFF;
}
QSlider::handle:horizontal:pressed {
    background: $ACCENT_HI;
}
QSlider::sub-page:horizontal:disabled, QSlider::groove:horizontal:disabled {
    background: #151B27;
}

/* ---- consola y progreso ---- */
QPlainTextEdit#console {
    background-color: #06090F;
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
    color: #A9B8CE;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
    selection-background-color: #1F4C3C;
    padding: 8px;
}
QPlainTextEdit#console:hover {
    border-color: $BORDER;
}

QProgressBar {
    background-color: #101724;
    border: 1px solid $BORDER_SOFT;
    border-radius: 5px;
    height: 7px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 $ACCENT_DIM, stop:1 $ACCENT);
    border-radius: 4px;
}

/* ---- scrollbars ---- */
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: #2B3850;
    border-radius: 5px;
    min-height: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:vertical:hover {
    background: #3D4F6E;
    background-clip: padding;
}
QScrollBar::handle:vertical:pressed {
    background: $ACCENT_DIM;
    background-clip: padding;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
QScrollBar:horizontal {
    background: transparent;
    height: 10px;
    margin: 2px 4px;
}
QScrollBar::handle:horizontal {
    background: #2B3850;
    border-radius: 5px;
    min-width: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:horizontal:hover {
    background: #3D4F6E;
    background-clip: padding;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* ---- dialogos, tooltips, divisores ---- */
QDialog {
    background-color: $BG_ALT;
}
QToolTip {
    background-color: $SURFACE_ALT;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 8.5pt;
}
QMessageBox {
    background-color: $SURFACE;
}
QFrame#divider {
    background-color: $BORDER_SOFT;
    max-height: 1px;
    border: none;
}

/* ---- barra lateral ---- */
QWidget#sidebar {
    background-color: $BG_ALT;
    border-right: 1px solid $BORDER_SOFT;
}
QWidget#statusBar {
    background-color: $BG_ALT;
    border-top: 1px solid $BORDER_SOFT;
}
QLabel#navTitle {
    color: $TEXT_FAINT;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1.8px;
    padding: 4px 12px 2px 12px;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 9px;
    color: $TEXT_DIM;
    text-align: left;
    padding: 8px 12px;
    font-size: 9.5pt;
    font-weight: 600;
    min-height: 16px;
}
QPushButton#navButton:hover {
    background-color: $SURFACE_HOVER;
    color: $TEXT;
}
QPushButton#navButton:pressed {
    background-color: $SURFACE_PRESSED;
}
QPushButton#navButton[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 rgba(61,220,151,0.18), stop:1 rgba(61,220,151,0.07));
    border-color: rgba(61, 220, 151, 0.30);
    color: $ACCENT;
    font-weight: 700;
}
QLabel#navBadge {
    color: $TEXT_FAINT;
    font-size: 8pt;
}

/* ---- paginas ---- */
QWidget#page {
    background: transparent;
}
QLabel#pageTitle {
    color: $TEXT;
    font-size: 17pt;
    font-weight: 800;
    letter-spacing: 0.4px;
}
QLabel#pageSubtitle {
    color: $TEXT_DIM;
    font-size: 9pt;
    letter-spacing: 0.2px;
}
QFrame#pageHeader {
    background: transparent;
    border: none;
}

/* ---- listas y tablas ---- */
QTableWidget, QListWidget, QTreeWidget {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 10px;
    gridline-color: $BORDER_SOFT;
    color: $TEXT;
    font-size: 8.5pt;
    selection-background-color: rgba(61, 220, 151, 0.14);
    selection-color: $TEXT;
    outline: none;
}
QTableWidget::item, QListWidget::item, QTreeWidget::item {
    padding: 4px 10px;
    border: none;
}
QTableWidget::item:hover, QListWidget::item:hover,
QTreeWidget::item:hover {
    background-color: $SURFACE_HOVER;
}
QHeaderView::section {
    background-color: $SURFACE_ALT;
    color: $TEXT_FAINT;
    border: none;
    border-bottom: 1px solid $BORDER;
    padding: 6px 11px;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QTableCornerButton::section {
    background-color: $SURFACE_ALT;
    border: none;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: rgba(61, 220, 151, 0.14);
    color: $TEXT;
}
QTreeWidget::branch {
    background: transparent;
}

/* ---- tarjetas de estadistica ---- */
QFrame#statCard {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER_SOFT;
    border-radius: 12px;
}
QFrame#statCard:hover {
    border-color: $BORDER;
}
QLabel#statValue {
    color: $TEXT;
    font-size: 14pt;
    font-weight: 800;
}
QLabel#statCaption {
    color: $TEXT_FAINT;
    font-size: 8pt;
    letter-spacing: 0.8px;
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
    return QSS.substitute(**COLORS, CHEVRON=assets["chevron"],
                          CHECK=assets["check"])


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet())
