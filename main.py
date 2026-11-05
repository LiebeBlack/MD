"""Punto de entrada de AZeroCraft Launcher."""

import sys


def _check_python() -> None:
    """PyQt6 requiere CPython compilado con GIL (no free-threaded)."""
    gil_disabled = getattr(sys, "_is_gil_enabled", lambda: True)
    try:
        freethreaded = not gil_disabled()
    except TypeError:
        freethreaded = False
    if freethreaded:
        print(
            "Error: este Python es una compilacion free-threaded (3.13t+) "
            "y PyQt6 no es compatible con ella.\n"
            "Soluciones:\n"
            "  - Ejecuta con el Python normal:  py -3.15 main.py\n"
            "  - O usa el ejecutable compilado:  dist\\AZeroCraft\\AZeroCraft.exe",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    _check_python()
    from azero.app import main
    raise SystemExit(main())
