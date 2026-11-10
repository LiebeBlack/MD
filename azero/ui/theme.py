"""Temas visuales estilo Office 365/Fluent: claro y oscuro, iconos y QSS."""

from __future__ import annotations

from pathlib import Path
from string import Template

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QIcon, QPainter, QPainterPath,
                         QPalette, QPen, QPixmap)
from PyQt6.QtWidgets import QApplication

from .. import paths
from ..branding import brand_icon

# --------------------------------------------------------------------------
# Escala de la interfaz. Todas las paginas usan estos valores para que los
# margenes, separaciones y anchos sean consistentes entre pantallas.
# --------------------------------------------------------------------------
PAGE_MARGIN = 18
PAGE_SPACING = 12
CARD_MARGIN = 14
CARD_SPACING = 8
COLUMN_GAP = 12
CONTENT_MAX_WIDTH = 1120

# Paletas Office 365 / Fluent. Cada tema define todos los tokens del QSS,
# incluidos los colores "sueltos" (consola, foco de campos, gradientes).
LIGHT = {
    "BG": "#F3F2F1",
    "BG_ALT": "#FAF9F8",
    "SURFACE": "#FFFFFF",
    "SURFACE_ALT": "#F3F2F1",
    "SURFACE_HOVER": "#EDEBE9",
    "SURFACE_PRESSED": "#E1DFDD",
    "BORDER": "#D2D0CE",
    "BORDER_SOFT": "#E1DFDD",
    "BORDER_STRONG": "#A19F9D",
    "TEXT": "#201F1E",
    "TEXT_DIM": "#605E5C",
    "TEXT_FAINT": "#8A8886",
    "ACCENT": "#0F6CBD",
    "ACCENT_HI": "#106EBE",
    "ACCENT_DIM": "#0C518A",
    "ACCENT_DEEP": "#0A3D66",
    "ACCENT_TEXT": "#FFFFFF",
    "DANGER": "#C50F1F",
    "WARN": "#CA5010",
    # Tokens extra para el QSS (rgb suelto para rgba(), fondos, degradados)
    "ACCENT_RGB": "15, 108, 189",
    "DANGER_RGB": "197, 15, 31",
    "FIELD_FOCUS": "#FBFCFE",
    "CONSOLE_BG": "#FAF9F8",
    "CONSOLE_TEXT": "#323130",
    "CONSOLE_SEL": "#D6E4F7",
    "OK_COLOR": "#107C10",
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
    "TEXT_DIM": "#BDBDBD",
    "TEXT_FAINT": "#969696",
    "ACCENT": "#3E8BDD",
    "ACCENT_HI": "#5592E4",
    "ACCENT_DIM": "#2B6CB8",
    "ACCENT_DEEP": "#1E4E8C",
    "ACCENT_TEXT": "#FFFFFF",
    "DANGER": "#F1707B",
    "WARN": "#F2C14E",
    "ACCENT_RGB": "62, 139, 221",
    "DANGER_RGB": "241, 112, 123",
    "FIELD_FOCUS": "#333333",
    "CONSOLE_BG": "#1E1E1E",
    "CONSOLE_TEXT": "#D4D4D4",
    "CONSOLE_SEL": "#264F78",
    "OK_COLOR": "#6CCB5F",
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


def _draw_chevron(path: Path, color: str, up: bool = False) -> None:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    if up:
        points = [QPointF(7, 15), QPointF(12, 10), QPointF(17, 15)]
    else:
        points = [QPointF(7, 10), QPointF(12, 15), QPointF(17, 10)]
    painter.drawPolyline(points)
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


def nav_icon(kind: str, color: str, size: int = 32) -> QIcon:
    """Iconos de linea para las pestanas, sin recursos externos."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 32.0, size / 32.0)
    pen = QPen(QColor(color), 2.2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if kind == "play":
        path = QPainterPath()
        path.moveTo(10, 7)
        path.lineTo(25, 16)
        path.lineTo(10, 25)
        path.closeSubpath()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawPath(path)
    elif kind == "versions":
        painter.drawRoundedRect(QRectF(8, 10, 16, 14), 2.5, 2.5)
        painter.drawLine(QPointF(9, 14), QPointF(23, 14))
        painter.drawLine(QPointF(13, 7), QPointF(19, 7))
    elif kind == "account":
        painter.drawEllipse(QRectF(11, 6, 10, 10))
        path = QPainterPath()
        path.moveTo(7, 26)
        path.cubicTo(7.5, 19, 24.5, 19, 25, 26)
        painter.drawPath(path)
    elif kind == "settings":
        for y, knob in ((10, 13), (16, 20), (22, 11)):
            painter.drawLine(QPointF(7, y), QPointF(25, y))
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(knob, y), 2.6, 2.6)
            painter.setBrush(Qt.BrushStyle.NoBrush)
    else:  # about
        painter.drawEllipse(QRectF(6, 6, 20, 20))
        painter.setBrush(QColor(color))
        painter.drawEllipse(QPointF(16, 11), 1.3, 1.3)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawLine(QPointF(16, 15), QPointF(16, 23))
    painter.end()
    return QIcon(pixmap)


def generate_assets(palette: dict | None = None) -> dict[str, str]:
    palette = palette or COLORS
    folder = _ui_assets_dir()
    chevron = folder / "chevron.png"
    chevron_up = folder / "chevron_up.png"
    check = folder / "check.png"
    _draw_chevron(chevron, palette["TEXT_DIM"])
    _draw_chevron(chevron_up, palette["TEXT_DIM"], up=True)
    _draw_check(check, palette["ACCENT_TEXT"])
    return {
        "chevron": chevron.as_posix(),
        "chevron_up": chevron_up.as_posix(),
        "check": check.as_posix(),
    }


def build_palette(theme_name: str = "light") -> QPalette:
    """QPalette real del tema.

    El QSS pinta casi todo, pero Qt dibuja algunos elementos con la paleta
    (menus contextuales, icono de limpiar de QLineEdit, flechas nativas,
    tooltips). Sin esto, el modo oscuro mezcla piezas claras del tema Fusion.
    """
    p = THEMES.get(theme_name, LIGHT)
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: p["BG"],
        QPalette.ColorRole.WindowText: p["TEXT"],
        QPalette.ColorRole.Base: p["SURFACE"],
        QPalette.ColorRole.AlternateBase: p["SURFACE_ALT"],
        QPalette.ColorRole.ToolTipBase: p["SURFACE"],
        QPalette.ColorRole.ToolTipText: p["TEXT"],
        QPalette.ColorRole.PlaceholderText: p["TEXT_FAINT"],
        QPalette.ColorRole.Text: p["TEXT"],
        QPalette.ColorRole.Button: p["SURFACE"],
        QPalette.ColorRole.ButtonText: p["TEXT"],
        QPalette.ColorRole.BrightText: p["DANGER"],
        QPalette.ColorRole.Link: p["ACCENT"],
        QPalette.ColorRole.Highlight: p["ACCENT"],
        QPalette.ColorRole.HighlightedText: p["ACCENT_TEXT"],
        QPalette.ColorRole.Light: p["SURFACE_HOVER"],
        QPalette.ColorRole.Midlight: p["SURFACE_ALT"],
        QPalette.ColorRole.Mid: p["BORDER"],
        QPalette.ColorRole.Dark: p["BORDER_STRONG"],
        QPalette.ColorRole.Shadow: p["BG"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    disabled = QPalette.ColorGroup.Disabled
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(disabled, role, QColor(p["TEXT_FAINT"]))
    palette.setColor(disabled, QPalette.ColorRole.Base,
                     QColor(p["SURFACE_ALT"]))
    palette.setColor(disabled, QPalette.ColorRole.Button,
                     QColor(p["SURFACE_ALT"]))
    palette.setColor(disabled, QPalette.ColorRole.Highlight,
                     QColor(p["BORDER"]))
    return palette


def app_icon() -> QIcon:
    """Icono de la app: la misma marca vectorial que el .ico e instalador."""
    return brand_icon()


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

/* ---- tarjetas y paneles ---- */
QFrame#card {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
}
QFrame#softPanel {
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
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
QLabel#sectionLabel {
    color: $TEXT_FAINT;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.9px;
    padding-top: 1px;
}
QLabel#muted {
    color: $TEXT_DIM;
    font-size: 8.5pt;
}
QLabel#faint {
    color: $TEXT_FAINT;
    font-size: 8.5pt;
}
QLabel#mono {
    color: $TEXT_FAINT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8.5pt;
}
QLabel#valueLabel {
    color: $TEXT;
    font-weight: 600;
}
QLabel#appTitle {
    color: $TEXT;
    font-size: 16pt;
    font-weight: 700;
}
QLabel#accountName {
    color: $TEXT;
    font-size: 13pt;
    font-weight: 700;
}
QLabel#codeLabel {
    color: $ACCENT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 22pt;
    font-weight: 800;
    letter-spacing: 2px;
    padding: 4px 0;
}
QLabel#emptyState {
    color: $TEXT_FAINT;
    font-size: 8.5pt;
    font-style: italic;
    padding: 14px;
}
QLabel#pill {
    background-color: rgba($ACCENT_RGB, 0.10);
    color: $ACCENT;
    border: 1px solid rgba($ACCENT_RGB, 0.28);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.7px;
}
QLabel#pillDim {
    background-color: $SURFACE_ALT;
    color: $TEXT_DIM;
    border: 1px solid $BORDER;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.7px;
}
QLabel#pillAccent {
    background-color: rgba($ACCENT_RGB, 0.14);
    color: $ACCENT;
    border: 1px solid rgba($ACCENT_RGB, 0.40);
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.7px;
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
    color: $OK_COLOR;
    font-size: 8.5pt;
    font-weight: 600;
}
QLabel#statusDot {
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    background-color: $TEXT_FAINT;
}
QLabel#statusDot[kind="ok"] {
    background-color: $OK_COLOR;
}
QLabel#statusDot[kind="error"] {
    background-color: $DANGER;
}
QLabel#statusDot[kind="busy"] {
    background-color: $WARN;
}

/* ---- campos de texto ---- */
QLineEdit {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 18px;
    selection-background-color: rgba($ACCENT_RGB, 0.22);
    selection-color: $TEXT;
}
QLineEdit:hover {
    border-color: $BORDER_STRONG;
}
QLineEdit:focus {
    border: 2px solid $ACCENT;
    background-color: $FIELD_FOCUS;
    padding: 5px 9px;
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
QLineEdit#nameEdit:hover {
    background-color: $SURFACE;
    border-color: $BORDER;
}
QLineEdit#nameEdit:focus {
    background-color: $SURFACE;
    border: 1px solid $ACCENT;
    padding: 2px 6px;
}

/* ---- combos ---- */
QComboBox {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 30px 6px 10px;
    min-height: 18px;
}
QComboBox:hover {
    border-color: $BORDER_STRONG;
}
QComboBox:focus {
    border: 2px solid $ACCENT;
    background-color: $FIELD_FOCUS;
    padding: 5px 29px 5px 9px;
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
    padding: 5px 9px;
    border-radius: 5px;
    min-height: 18px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: $SURFACE_HOVER;
}
QComboBox QAbstractItemView::item:selected {
    background-color: rgba($ACCENT_RGB, 0.12);
}

/* ---- selector de versiones agrupado ---- */
QPushButton#versionPicker {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 18px;
    color: $TEXT;
    font-size: 9.5pt;
    font-weight: 600;
    text-align: left;
}
QPushButton#versionPicker:hover {
    border-color: $BORDER_STRONG;
    background-color: $SURFACE_HOVER;
}
QPushButton#versionPicker:pressed {
    background-color: $SURFACE_PRESSED;
}
QPushButton#versionPicker:focus {
    border: 2px solid $ACCENT;
    background-color: $FIELD_FOCUS;
    padding: 5px 11px;
}
QPushButton#versionPicker:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
}
QFrame#versionPopup {
    background-color: $SURFACE;
    border: 1px solid $BORDER_STRONG;
    border-radius: 8px;
}
QTreeWidget#versionTree {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    outline: none;
}
QTreeWidget#versionTree:focus {
    border-color: $ACCENT;
}
QTreeWidget#versionTree::item {
    padding: 6px 10px;
    border-radius: 5px;
    min-height: 22px;
}
QTreeWidget#versionTree::item:hover {
    background-color: $SURFACE_HOVER;
}
QTreeWidget#versionTree::item:selected {
    background-color: rgba($ACCENT_RGB, 0.12);
    color: $TEXT;
}

/* ---- botones ---- */
QAbstractButton:focus {
    border-color: $ACCENT_DIM;
}
QPushButton {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 18px;
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
    background-color: $ACCENT;
    border: 1px solid $ACCENT_DEEP;
    border-radius: 6px;
    color: $ACCENT_TEXT;
    font-size: 11pt;
    font-weight: 700;
    letter-spacing: 0.6px;
    padding: 10px 16px;
}
QPushButton#playButton:hover {
    background-color: $ACCENT_HI;
    border-color: $ACCENT_DIM;
}
QPushButton#playButton:pressed {
    background-color: $ACCENT_DIM;
}
QPushButton#playButton:focus {
    border: 2px solid $TEXT;
    padding: 9px 15px;
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
    padding: 6px 10px;
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
QPushButton#ghostButton:focus {
    color: $TEXT;
    border-color: $ACCENT;
    background-color: rgba($ACCENT_RGB, 0.06);
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
    padding: 6px 12px;
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
QPushButton#accentGhost:focus {
    border: 2px solid $ACCENT;
    padding: 5px 11px;
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
QPushButton#iconButton:focus {
    border-color: $ACCENT;
    color: $TEXT;
}
QPushButton#iconButton:disabled {
    color: $TEXT_FAINT;
}
QPushButton#dangerButton {
    background: transparent;
    border: 1px solid rgba($DANGER_RGB, 0.35);
    border-radius: 6px;
    color: $DANGER;
    padding: 6px 12px;
    font-weight: 600;
}
QPushButton#dangerButton:hover {
    background-color: rgba($DANGER_RGB, 0.08);
    border-color: rgba($DANGER_RGB, 0.55);
}
QPushButton#dangerButton:pressed {
    background-color: rgba($DANGER_RGB, 0.14);
}
QPushButton#dangerButton:focus {
    border: 2px solid $DANGER;
    padding: 5px 11px;
}
QPushButton#dangerButton:disabled {
    color: $TEXT_FAINT;
    border-color: rgba($DANGER_RGB, 0.15);
}
QPushButton#primaryButton {
    background-color: $ACCENT;
    border: 1px solid $ACCENT_DEEP;
    border-radius: 6px;
    color: $ACCENT_TEXT;
    font-weight: 600;
    padding: 6px 14px;
}
QPushButton#primaryButton:hover {
    background-color: $ACCENT_HI;
    border-color: rgba(255, 255, 255, 0.25);
}
QPushButton#primaryButton:pressed {
    background-color: $ACCENT_DIM;
}
QPushButton#primaryButton:focus {
    border: 2px solid $ACCENT_TEXT;
    padding: 5px 13px;
}
QPushButton#primaryButton:disabled {
    background-color: $SURFACE_ALT;
    border-color: $BORDER_SOFT;
    color: $TEXT_FAINT;
}
QPushButton#segButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    color: $TEXT_DIM;
    padding: 6px 16px;
    font-weight: 600;
}
QPushButton#segButton:hover {
    color: $TEXT;
    background-color: $SURFACE_HOVER;
}
QPushButton#segButton:checked {
    background-color: $SURFACE;
    border-color: $BORDER;
    color: $ACCENT;
    font-weight: 700;
}
QPushButton#segButton:focus {
    border-color: $ACCENT;
}
QFrame#segmented {
    background-color: $SURFACE_ALT;
    border: 1px solid $BORDER;
    border-radius: 8px;
}
QPushButton#presetButton {
    background: transparent;
    border: 1px solid $BORDER_SOFT;
    border-radius: 5px;
    color: $TEXT_DIM;
    padding: 3px 9px;
    font-size: 8pt;
    font-weight: 600;
}
QPushButton#presetButton:hover {
    color: $TEXT;
    background-color: $SURFACE_HOVER;
    border-color: $BORDER;
}
QPushButton#presetButton:checked {
    background-color: rgba($ACCENT_RGB, 0.11);
    border-color: rgba($ACCENT_RGB, 0.40);
    color: $ACCENT;
}
QPushButton#presetButton:focus {
    border-color: $ACCENT;
}
QPushButton#presetButton:disabled {
    color: $TEXT_FAINT;
    border-color: $BORDER_SOFT;
}

/* ---- spin boxes ---- */
QSpinBox {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 8px;
    min-height: 18px;
    color: $TEXT;
}
QSpinBox:hover {
    border-color: $BORDER_STRONG;
}
QSpinBox:focus {
    border: 2px solid $ACCENT;
    background-color: $FIELD_FOCUS;
    padding: 5px 7px;
}
QSpinBox:disabled {
    color: $TEXT_FAINT;
    background-color: $SURFACE_ALT;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 20px;
    border: none;
    border-left: 1px solid $BORDER_SOFT;
    background: transparent;
}
QSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    border-top-right-radius: 6px;
}
QSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    border-bottom-right-radius: 6px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: $SURFACE_HOVER;
}
QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {
    background-color: $SURFACE_PRESSED;
}
QSpinBox::up-arrow {
    image: url("$CHEVRON_UP");
    width: 9px;
    height: 9px;
}
QSpinBox::down-arrow {
    image: url("$CHEVRON");
    width: 9px;
    height: 9px;
}

/* ---- checks y sliders ---- */
QCheckBox {
    color: $TEXT_DIM;
    spacing: 8px;
    font-size: 8.5pt;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 1px 3px;
}
QCheckBox:hover {
    color: $TEXT;
}
QCheckBox:focus {
    color: $TEXT;
    border-color: $ACCENT;
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
    background-color: $ACCENT;
    border-radius: 3px;
}
QSlider::add-page:horizontal {
    background: $SURFACE_PRESSED;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: $SURFACE;
    width: 14px;
    height: 14px;
    margin: -5px 0;
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
QPlainTextEdit#console, QTextEdit#console {
    background-color: $CONSOLE_BG;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
    color: $CONSOLE_TEXT;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 8pt;
    selection-background-color: $CONSOLE_SEL;
    padding: 8px;
}
QPlainTextEdit#console:hover, QTextEdit#console:hover {
    border-color: $BORDER;
}
QPlainTextEdit#console:focus, QTextEdit#console:focus {
    border-color: $ACCENT;
}

QProgressBar {
    background-color: $SURFACE_HOVER;
    border: 1px solid $BORDER_SOFT;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 $ACCENT, stop:1 $ACCENT_HI);
    border-radius: 3px;
}

/* ---- scrollbars ---- */
QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: $BORDER_STRONG;
    border-radius: 5px;
    min-height: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:vertical:hover {
    background: $TEXT_FAINT;
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
    height: 9px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: $BORDER_STRONG;
    border-radius: 5px;
    min-width: 30px;
    border: 2px solid transparent;
    background-clip: padding;
}
QScrollBar::handle:horizontal:hover {
    background: $TEXT_FAINT;
    background-clip: padding;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* ---- menus, dialogos, tooltips, divisores ---- */
QMenu {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 8px;
    padding: 5px;
}
QMenu::item {
    background: transparent;
    color: $TEXT;
    padding: 6px 22px 6px 14px;
    border-radius: 5px;
}
QMenu::item:selected {
    background-color: rgba($ACCENT_RGB, 0.14);
    color: $TEXT;
}
QMenu::item:disabled {
    color: $TEXT_FAINT;
}
QMenu::separator {
    height: 1px;
    background: $BORDER_SOFT;
    margin: 4px 8px;
}
QToolButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 5px;
    padding: 3px;
}
QToolButton:hover {
    background-color: $SURFACE_HOVER;
    border-color: $BORDER_SOFT;
}
QDialog {
    background-color: $BG_ALT;
}
QDialogButtonBox QPushButton, QMessageBox QPushButton {
    min-width: 84px;
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

/* ---- barra superior, navegacion y barra de estado ---- */
QWidget#appBar {
    background-color: $SURFACE;
    border-bottom: 1px solid $BORDER_SOFT;
}
QTabBar#browserTabs {
    background: transparent;
    qproperty-drawBase: 0;
}
QTabBar#browserTabs::tab {
    background: transparent;
    color: $TEXT_DIM;
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    margin: 0 2px;
    min-width: 0;
}
QTabBar#browserTabs::tab:hover {
    background-color: $SURFACE_HOVER;
    color: $TEXT;
}
QTabBar#browserTabs::tab:selected {
    background-color: rgba($ACCENT_RGB, 0.10);
    color: $ACCENT;
    font-weight: 600;
}
QTabBar#browserTabs::tab:selected:hover {
    background-color: rgba($ACCENT_RGB, 0.14);
}
QTabBar#browserTabs::tab:disabled {
    color: $TEXT_FAINT;
}
QWidget#statusBar {
    background-color: $SURFACE;
    border-top: 1px solid $BORDER_SOFT;
}

/* ---- paginas ---- */
QWidget#page {
    background: transparent;
}
QLabel#pageTitle {
    color: $TEXT;
    font-size: 13.5pt;
    font-weight: 700;
    letter-spacing: 0.1px;
}
QLabel#pageSubtitle {
    color: $TEXT_DIM;
    font-size: 8.5pt;
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
QTableWidget:focus, QListWidget:focus, QTreeWidget:focus {
    border-color: $ACCENT;
}
QTableWidget {
    alternate-background-color: $SURFACE_ALT;
}
QTableWidget::item, QListWidget::item, QTreeWidget::item {
    padding: 5px 10px;
    border: none;
}
QTableWidget::item:hover, QListWidget::item:hover,
QTreeWidget::item:hover {
    background-color: $SURFACE_HOVER;
}
QTableWidget::item:focus, QListWidget::item:focus,
QTreeWidget::item:focus {
    border: 1px solid rgba($ACCENT_RGB, 0.45);
}
QTableWidget::item:selected {
    background-color: rgba($ACCENT_RGB, 0.12);
    color: $TEXT;
}
QHeaderView::section {
    background-color: $SURFACE_ALT;
    color: $TEXT_FAINT;
    border: none;
    border-bottom: 1px solid $BORDER_SOFT;
    padding: 6px 9px;
    font-size: 7.5pt;
    font-weight: 700;
    letter-spacing: 0.9px;
}
QHeaderView::section:hover {
    color: $TEXT_DIM;
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
    background-color: $SURFACE;
    border: 1px solid $BORDER_SOFT;
    border-radius: 8px;
}
QFrame#statCard:hover {
    border-color: rgba($ACCENT_RGB, 0.45);
}
QLabel#statValue {
    color: $TEXT;
    font-size: 13pt;
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
                          CHEVRON_UP=assets["chevron_up"],
                          CHECK=assets["check"])


def apply_theme(app: QApplication, theme_name: str = "light") -> None:
    """Aplica el tema indicado ('light' u 'dark') a toda la aplicacion."""
    global COLORS, _active
    theme_name = theme_name if theme_name in THEMES else "light"
    _active = theme_name
    palette = THEMES[theme_name]
    COLORS = dict(palette)
    app.setStyle("Fusion")
    app.setPalette(build_palette(theme_name))
    app.setWindowIcon(app_icon())
    font = QFont("Segoe UI", 10)
    font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(font)
    app.setStyleSheet(build_stylesheet(theme_name))


def current_theme_name() -> str:
    return _active
