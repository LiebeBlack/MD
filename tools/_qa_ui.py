"""QA: construye la ventana principal en modo offscreen."""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("AZEROCRAFT_DATA", os.path.join(ROOT, "data_qa_tmp"))

try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from azero.settings import Settings
    settings = Settings.load()
    print("settings ok")
    from azero.ui.main_window import MainWindow
    window = MainWindow(settings)
    print("UI OK:", window.windowTitle())
except SystemExit as exc:
    print("SystemExit:", exc)
except Exception:
    traceback.print_exc()
    sys.exit(1)
