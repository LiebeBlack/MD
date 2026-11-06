"""Temas visuales estilo Office 365/Fluent: claro y oscuro, iconos y QSS."""

from __future__ import annotations

from pathlib import Path
from string import Template

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QIcon, QLinearGradient, QPainter,
                         QPainterPath, QPalette, QPen, QPixmap)
from PyQt6.QtWidgets import QApplication

from .. import paths

# --------------------------------------------------------------------------
# Escala de la interfaz. Todas las paginas usan estos valores para que los
# margenes, separaciones y anchos sean consistentes entre pantallas.
# --------------------------------------------------------------------------
PAGE_MARGIN = 16
PAGE_SPACING = 12
CARD_MARGIN = 12
CARD_SPACING = 8
COLUMN_GAP = 12
CONTENT_MAX_WIDTH = 1280
SIDEBAR_WIDTH = 200

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
    "BORDER_SOFT": "#E6E4E2",
    "BORDER_STRONG": "#A19F9D",
    "TEXT": "#252423",
    "TEXT_DIM": "#545250",
    "TEXT_FAINT": "#737170",
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
    "TEXT_DIM": "#BDBDBD",
    "TEXT_FAINT": "#969696",
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


def _draw_clear(path: Path, color: str) -> None:
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    painter.drawLine(QPointF(8, 8), QPointF(16, 16))
    painter.drawLine(QPointF(16, 8), QPointF(8, 16))
    painter.end()
    pixmap.save(str(path))


def generate_assets(palette: dict | None = None) -> dict[str, str]:
    palette = palette or COLORS
    folder = _ui_assets_dir()
    chevron = folder / "chevron.png"
    chevron_up = folder / "chevron_up.png"
    check = folder / "check.png"
    clear = folder / "clear.png"
    _draw_chevron(chevron, palette["TEXT_DIM"])
    _draw_chevron(chevron_up, palette["TEXT_DIM"], up=True)
    _draw_check(check, palette["ACCENT_TEXT"])
    _draw_clear(clear, palette["TEXT_FAINT"])
    return {
        "chevron": chevron.as_posix(),
        "chevron_up": chevron_up.as_posix(),
        "check": check.as_posix(),
        "clear": clear.as_posix(),
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
    pixmap = QPixmap(128, 128)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(4, 4, 120, 120), 26, 26)
    gradient = QLinearGradient(0, 0, 128, 128)
    gradient.setColorAt(0.0, QColor("#4A95E6"))
    gradient.setColorAt(1.0, QColor("#185ABD"))
    painter.fillPath(path, gradient)

    # Brillo superior sutil, sin depender de imagenes externas.
    shine = QLinearGradient(0, 0, 0, 128)
    shine.setColorAt(0.0, QColor(255, 255, 255, 46))
    shine.setColorAt(0.55, QColor(255, 255, 255, 0))
    painter.fillPath(path, shine)
    painter.setPen(QPen(QColor(255, 255, 255, 60), 2))
    painter.drawRoundedRect(QRectF(5, 5, 118, 118), 25, 25)

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
    font-size: 14pt;
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
    letter-spacing: 1.3px;
    padding-top: 1px;
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
    font-weight: 600;
}
QLabel#appTitle {
    color: $TEXT;
    font-size: 18pt;
    font-weight: 800;
}
QLabel#emptyState {
    color: $TEXT_FAINT;
    font-size: 8.5pt;
    font-style: italic;
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
    min-height: 17px;
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

/* ---- botones ---- */
QAbstractButton:focus {
    border-color: $ACCENT_DIM;
}
QPushButton {
    background-color: $SURFACE;
    border: 1px solid $BORDER;
    border-radius: 6px;
    padding: 6px 12px;
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
    border-radius: 8px;
    color: $ACCENT_TEXT;
    font-size: 12pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 13px 18px;
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
QPushButton#playButton:focus {
    border: 2px solid $TEXT;
    padding: 12px 17px;
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
    padding: 5px 9px;
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
QPushButton#accentGhost:focus {
    border: 2px solid $ACCENT;
    padding: 4px 10px;
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
QPushButton#dangerButton:focus {
    border: 2px solid $DANGER;
    padding: 4px 10px;
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
    padding: 6px 13px;
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
    padding: 5px 12px;
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
    padding: 5px 16px;
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
    min-height: 17px;
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
                                stop:0 $ACCENT_DIM, stop:1 $ACCENT);
    border-radius: 3px;
}

/* ---- scrollbars ---- */
QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 2px;
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
    height: 9px;
    margin: 2px;
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
    letter-spacing: 1.3px;
    padding: 8px 12px 2px 12px;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-left: 3px solid transparent;
    border-radius: 6px;
    color: $TEXT_DIM;
    text-align: left;
    padding: 7px 10px 7px 8px;
    font-size: 9pt;
    font-weight: 600;
    min-height: 20px;
}
QPushButton#navButton:hover {
    background-color: rgba($ACCENT_RGB, 0.06);
    color: $TEXT;
}
QPushButton#navButton:pressed {
    background-color: rgba($ACCENT_RGB, 0.12);
}
QPushButton#navButton:focus {
    border-color: $ACCENT;
    color: $TEXT;
}
QPushButton#navButton[active="true"] {
    background-color: rgba($ACCENT_RGB, 0.12);
    border-color: rgba($ACCENT_RGB, 0.20);
    border-left: 3px solid $ACCENT;
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
    font-size: 16pt;
    font-weight: 800;
    letter-spacing: 0.1px;
}
QLabel#pageSubtitle {
    color: $TEXT_DIM;
    font-size: 9pt;
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
    padding: 4px 8px;
    border: none;
}
QTableWidget::item:hover, QListWidget::item:hover,
QTreeWidget::item:hover {
    background-color: $SURFACE_HOVER;
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
                          CHECK=assets["check"], CLEAR=assets["clear"])


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
