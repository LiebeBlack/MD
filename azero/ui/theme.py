"""Temas visuales estilo Office 365/Fluent: claro y oscuro, iconos y QSS."""

from __future__ import annotations

from pathlib import Path
from string import Template

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPen, QPixmap)
from PyQt6.QtWidgets import QApplication

from .. import paths

# Paletas Office 365 / Fluent. Cada tema define todos los tokens del QSS,
# incluidos los colores "sueltos" (consola, foco de campos, gradientes).
LIGHT = {
    "BG": "#F5F5F5",
    "BG_ALT": "#FFFFFF",
    "SURFACE": "#FFFFFF",
    "SURFACE_ALT": "#F5F5F5",
    "SURFACE_HOVER": "#EBEBEB",
    "SURFACE_PRESSED": "#E1E1E1",
    "BORDER": "#D2D0CE",
    "BORDER_SOFT": "#EBEBEB",
    "BORDER_STRONG": "#A19F9D",
    "TEXT": "#252423",
    "TEXT_DIM": "#605E5C",
    "TEXT_FAINT": "#8A8886",
    "ACCENT": "#185ABD",
    "ACCENT_HI": "#0F6CBD",
    "ACCENT_DIM": "#124A9E",
    "ACCENT_DEEP": "#0B3D77",
    "ACCENT_TEXT": "#FFFFFF",
    "ACCENT2": "#881798",
    "INFO": "#0F6CBD",
    "DANGER": "#C50F1F",
    "WARN": "#CA5010",
    # Tokens extra para el QSS (rgb suelto para rgba(), fondos, degradados)
    "ACCENT_RGB": "24, 90, 189",
    "DANGER_RGB": "197, 15, 31",
    "FIELD_FOCUS": "#FBFCFE",
    "CONSOLE_BG": "#FAF9F8",
    "CONSOLE_TEXT": "#323130",
    "CONSOLE_SEL": "#D6E4F7",
    "OK_COLOR": "#107C10",
    "CARD_A": "#FFFFFF",
    "CARD_B": "#FBFBFB",
    "PANEL_A": "#FFFFFF",
    "PANEL_B": "#F7F7F7",
    "PLAY_A": "#3E8BDD",
    "PLAY_B": "#185ABD",
    "PLAY_A_HI": "#5592E4",
    "PLAY_B_HI": "#0F6CBD",
}

DARK = {
    "BG": "#1F1F1F",
    "BG_ALT": "#252526",
    "SURFACE": "#2D2D2D",
    "SURFACE_ALT": "#333333",
    "SURFACE_HOVER": "#3B3B3B",
    "SURFACE_PRESSED": "#424242",
    "BORDER": "#4A4A4A",
    "BORDER_SOFT": "#3A3A3A",
    "BORDER_STRONG": "#6E6E6E",
    "TEXT": "#FFFFFF",
    "TEXT_DIM": "#ADADAD",
    "TEXT_FAINT": "#8A8A8A",
    "ACCENT": "#3E8BDD",
    "ACCENT_HI": "#5592E4",
    "ACCENT_DIM": "#2B6CB8",
    "ACCENT_DEEP": "#1E4E8C",
    "ACCENT_TEXT": "#FFFFFF",
    "ACCENT2": "#B180D7",
    "INFO": "#6CB6FF",
    "DANGER": "#F1707B",
    "WARN": "#F2C14E",
    "ACCENT_RGB": "62, 139, 221",
    "DANGER_RGB": "241, 112, 123",
    "FIELD_FOCUS": "#333333",
    "CONSOLE_BG": "#1E1E1E",
    "CONSOLE_TEXT": "#D4D4D4",
    "CONSOLE_SEL": "#264F78",
    "OK_COLOR": "#6CCB5F",
    "CARD_A": "#2D2D2D",
    "CARD_B": "#2B2B2B",
    "PANEL_A": "#252526",
    "PANEL_B": "#222222",
    "PLAY_A": "#5592E4",
    "PLAY_B": "#2B6CB8",
    "PLAY_A_HI": "#6FA8F5",
    "PLAY_B_HI": "#3E8BDD",
}

THEMES = {"light": LIGHT, "dark": DARK}
THEME_NAMES = {"light": "Claro", "dark": "Oscuro"}

# Paleta activa: la leen paginas/widgets via theme.COLORS[...].
COLORS = dict(LIGHT)
_active = "light"


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


def generate_assets(palette: dict | None = None) -> dict[str, str]:
    palette = palette or COLORS
    folder = _ui_assets_dir()
    chevron = folder / "chevron.png"
    check = folder / "check.png"
    _draw_chevron(chevron, palette["TEXT_DIM"])
    _draw_check(check, palette["ACCENT_TEXT"])
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
    path.addRoundedRect(QRectF(4, 4, 120, 120), 26, 26)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0.0, QColor("#3E8BDD"))
    gradient.setColorAt(1.0, QColor("#185ABD"))
    painter.fillPath(path, gradient)

    font = QFont("Segoe UI", 58, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
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
    font-size: 9pt;
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

/* ---- tarjetas y paneles (degradado sutil tipo Fluent/Mica) ---- */
QFrame#card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $CARD_A, stop:1 $CARD_B);
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
}
QFrame#card:hover {
    border-color: $BORDER;
}
QFrame#softPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $CARD_A, stop:1 $CARD_B);
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
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
    font-size: 13pt;
    font-weight: 700;
    letter-spacing: 0.2px;
}
QLabel#brandAccent {
    color: $ACCENT;
}
QLabel#sectionLabel {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1.4px;
    padding-top: 2px;
}
QLabel#muted {
    color: $TEXT_DIM;
    font-size: 8pt;
    line-height: 1.35;
}
QLabel#faint {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
}
QLabel#mono {
    color: $TEXT_FAINT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 7.5pt;
}
QLabel#valueLabel {
    color: $TEXT;
    font-weight: 600;
}
QLabel#pill {
    background-color: rgba($ACCENT_RGB, 0.10);
    color: $ACCENT;
    border: 1px solid rgba($ACCENT_RGB, 0.28);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.8px;
}
QLabel#pillDim {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 7.5pt;
}
QLabel#statusLabel {
    color: $TEXT_DIM;
    font-size: 8pt;
}
QLabel#statusError {
    color: $DANGER;
    font-size: 8pt;
    font-weight: 600;
}
QLabel#statusOk {
    color: $OK_COLOR;
    font-size: 8pt;
    font-weight: 600;
}

/* ---- campos de texto ---- */
QLineEdit {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 5px 9px;
    selection-background-color: rgba($ACCENT_RGB, 0.22);
    selection-color: $TEXT;
}
QLineEdit:hover {
    border-color: $BORDER_STRONG;
}
QLineEdit:focus {
    border-color: $ACCENT;
    background-color: $FIELD_FOCUS;
}
QLineEdit:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
}
QLineEdit#nameEdit {
    font-size: 11pt;
    font-weight: 600;
    padding: 2px 6px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
}
QLineEdit#nameEdit:hover, QLineEdit#nameEdit:focus {
    background-color: $SURFACE;
    border-color: $BORDER;
}

/* ---- combos ---- */
QComboBox {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 5px 30px 5px 9px;
    min-height: 15px;
}
QComboBox:hover {
    border-color: $BORDER_STRONG;
}
QComboBox:focus {
    border-color: $ACCENT;
    background-color: $FIELD_FOCUS;
}
QComboBox:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
}
QComboBox::down-arrow {
    image: url("$CHEVRON");
    width: 13px;
    height: 13px;
}
QComboBox QAbstractItemView {
    background-color: $SURFACE;
    border: 1px solid $BORDER_STRONG;
    border-radius: 6px;
    padding: 5px;
    selection-background-color: rgba($ACCENT_RGB, 0.12);
    selection-color: $TEXT;
    outline: none;
}
QComboBox QAbstractItemView::item {
    padding: 4px 7px;
    border-radius: 5px;
    min-height: 15px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: $SURFACE_HOVER;
}
QComboBox QAbstractItemView::item:selected {
    background-color: rgba($ACCENT_RGB, 0.12);
}

/* ---- botones ---- */
QAbstractButton:focus {
    border-color: $ACCENT_DIM;
}
QPushButton {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 5px 11px;
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
    background-color: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
}
QPushButton#playButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $PLAY_A, stop:1 $PLAY_B);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 7px;
    color: $ACCENT_TEXT;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 12px 18px;
}
QPushButton#playButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $PLAY_A_HI, stop:1 $PLAY_B_HI);
    border-color: rgba(255, 255, 255, 0.28);
}
QPushButton#playButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $PLAY_B, stop:1 $ACCENT_DIM);
}
QPushButton#playButton:disabled {
    background: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
    color: $TEXT_FAINT;
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
    border-radius: 6px;
    color: $TEXT_DIM;
    padding: 4px 8px;
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
    background-color: rgba($ACCENT_RGB, 0.07);
    border: 1px solid rgba($ACCENT_RGB, 0.30);
    border-radius: 6px;
    color: $ACCENT;
    padding: 5px 11px;
    font-size: 9pt;
    font-weight: 600;
}
QPushButton#accentGhost:hover {
    background-color: rgba($ACCENT_RGB, 0.13);
    border-color: rgba($ACCENT_RGB, 0.50);
}
QPushButton#accentGhost:pressed {
    background-color: rgba($ACCENT_RGB, 0.20);
}
QPushButton#accentGhost:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
}
QPushButton#iconButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 5px;
    font-size: 10pt;
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
    border: 1px solid rgba($DANGER_RGB, 0.35);
    border-radius: 6px;
    color: $DANGER;
    padding: 5px 11px;
    font-weight: 600;
}
QPushButton#dangerButton:hover {
    background-color: rgba($DANGER_RGB, 0.08);
    border-color: rgba($DANGER_RGB, 0.55);
}
QPushButton#dangerButton:pressed {
    background-color: rgba($DANGER_RGB, 0.14);
}
QPushButton#dangerButton:disabled {
    color: $TEXT_FAINT;
    border-color: rgba($DANGER_RGB, 0.15);
}
QPushButton#primaryButton {
    background-color: $ACCENT;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: $ACCENT_TEXT;
    font-weight: 600;
    padding: 6px 12px;
}
QPushButton#primaryButton:hover {
    background-color: $ACCENT_HI;
    border-color: rgba(255, 255, 255, 0.25);
}
QPushButton#primaryButton:pressed {
    background-color: $ACCENT_DIM;
}
QPushButton#primaryButton:disabled {
    background-color: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
    color: $TEXT_FAINT;
}

/* ---- spin boxes ---- */
QSpinBox {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 5px 6px;
    min-height: 15px;
    color: $TEXT;
}
QSpinBox:hover {
    border-color: $BORDER_STRONG;
}
QSpinBox:focus {
    border-color: $ACCENT;
    background-color: $FIELD_FOCUS;
}
QSpinBox:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 22px;
    border: none;
    background: transparent;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: $SURFACE_HOVER;
    border-radius: 4px;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: $ACCENT_DIM;
}

/* ---- checks y sliders ---- */
QCheckBox {
    color: $TEXT_DIM;
    spacing: 8px;
    font-size: 8.5pt;
}
QCheckBox:hover {
    color: $TEXT;
}
QCheckBox:disabled {
    color: $TEXT_FAINT;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border-radius: 4px;
    border: 1px solid $BORDER_STRONG;
    background-color: $SURFACE;
}
QCheckBox::indicator:hover {
    border-color: $ACCENT_DIM;
    background-color: $SURFACE_HOVER;
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
    background-color: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
}

QSlider::groove:horizontal {
    height: 5px;
    background: $SURFACE_HOVER;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 $ACCENT_DIM, stop:1 $ACCENT);
    border-radius: 3px;
}
QSlider::add-page:horizontal {
    background: $SURFACE_PRESSED;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: $SURFACE;
    width: 13px;
    height: 13px;
    margin: -4px 0;
    border-radius: 8px;
    border: 2px solid $BORDER_STRONG;
}
QSlider::handle:horizontal:hover {
    border-color: $ACCENT;
    background: $FIELD_FOCUS;
}
QSlider::handle:horizontal:pressed {
    background: $ACCENT;
    border-color: $ACCENT;
}
QSlider::sub-page:horizontal:disabled, QSlider::groove:horizontal:disabled {
    background: $SURFACE_PRESSED;
}

/* ---- consola y progreso ---- */
QPlainTextEdit#console {
    background-color: $CONSOLE_BG;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
    color: $CONSOLE_TEXT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
    selection-background-color: $CONSOLE_SEL;
    padding: 8px;
}
QPlainTextEdit#console:hover {
    border-color: $BORDER;
}

QProgressBar {
    background-color: $SURFACE_HOVER;
    border: 1px solid $BORDER_SOFT;
    border-radius: 4px;
    height: 7px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 $ACCENT_DIM, stop:1 $ACCENT);
    border-radius: 3px;
}

/* ---- scrollbars ---- */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 2px;
}
QScrollBar::handle:vertical {
    background: $BORDER;
    border-radius: 5px;
    min-height: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:vertical:hover {
    background: $BORDER_STRONG;
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
    height: 8px;
    margin: 2px 2px;
}
QScrollBar::handle:horizontal {
    background: $BORDER;
    border-radius: 5px;
    min-width: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:horizontal:hover {
    background: $BORDER_STRONG;
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
    background-color: $SURFACE;
    color: $TEXT;
    border: 1px solid $BORDER_STRONG;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 8pt;
}
QMessageBox {
    background-color: $SURFACE;
}
QFrame#divider {
    background-color: $BORDER_SOFT;
    max-height: 1px;
    border: none;
}

/* ---- barra lateral y barra de estado (degradado sutil) ---- */
QWidget#sidebar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $PANEL_A, stop:1 $PANEL_B);
    border-right: 1px solid $BORDER_SOFT;
}
QWidget#statusBar {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 $PANEL_A, stop:1 $PANEL_B);
    border-top: 1px solid $BORDER_SOFT;
}
QLabel#navTitle {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1.4px;
    padding: 6px 12px 2px 12px;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: $TEXT_DIM;
    text-align: left;
    padding: 6px 10px;
    font-size: 9pt;
    font-weight: 600;
    min-height: 18px;
}
QPushButton#navButton:hover {
    background-color: rgba($ACCENT_RGB, 0.06);
    color: $TEXT;
}
QPushButton#navButton:pressed {
    background-color: rgba($ACCENT_RGB, 0.12);
}
QPushButton#navButton[active="true"] {
    background-color: rgba($ACCENT_RGB, 0.12);
    border-color: rgba($ACCENT_RGB, 0.20);
    color: $ACCENT;
    font-weight: 700;
}
QLabel#navBadge {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
}

/* ---- paginas ---- */
QWidget#page {
    background: transparent;
}
QLabel#pageTitle {
    color: $TEXT;
    font-size: 15pt;
    font-weight: 700;
    letter-spacing: 0.2px;
}
QLabel#pageSubtitle {
    color: $TEXT_DIM;
    font-size: 9pt;
    letter-spacing: 0.1px;
}
QFrame#pageHeader {
    background: transparent;
    border: none;
}

/* ---- listas y tablas ---- */
QTableWidget, QListWidget, QTreeWidget {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
    gridline-color: $BORDER_SOFT;
    color: $TEXT;
    font-size: 8.5pt;
    selection-background-color: rgba($ACCENT_RGB, 0.12);
    selection-color: $TEXT;
    outline: none;
}
QTableWidget {
    alternate-background-color: $SURFACE_ALT;
}
QTableWidget::item, QListWidget::item, QTreeWidget::item {
    padding: 3px 8px;
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
    border-bottom: 1px solid $BORDER_SOFT;
    padding: 5px 9px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 1px;
}
QTableCornerButton::section {
    background-color: $SURFACE_ALT;
    border: none;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: rgba($ACCENT_RGB, 0.12);
    color: $TEXT;
}
QTreeWidget::branch {
    background: transparent;
}

/* ---- tarjetas de estadistica ---- */
QFrame#statCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 $CARD_A, stop:1 $CARD_B);
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
}
QFrame#statCard:hover {
    border-color: $BORDER;
}
QLabel#statValue {
    color: $TEXT;
    font-size: 12pt;
    font-weight: 700;
}
QLabel#statCaption {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
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


def build_stylesheet(theme_name: str = "light") -> str:
    palette = THEMES.get(theme_name, LIGHT)
    assets = generate_assets(palette)
    return QSS.substitute(**palette, CHEVRON=assets["chevron"],
                          CHECK=assets["check"])


def apply_theme(app: QApplication, theme_name: str = "light") -> None:
    """Aplica el tema indicado ('light' u 'dark') a toda la aplicacion."""
    global COLORS, _active
    theme_name = theme_name if theme_name in THEMES else "light"
    _active = theme_name
    palette = THEMES[theme_name]
    COLORS = dict(palette)
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet(theme_name))


def current_theme_name() -> str:
    return _active
