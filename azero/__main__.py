"""Permite ejecutar el launcher con `python -m azero`."""

import sys


def _check_python() -> None:
    """PyQt6 requiere CPython compilado con GIL (no free-threaded)."""
    gil_enabled = getattr(sys, "_is_gil_enabled", None)
    if gil_enabled is not None:
        try:
            freethreaded = not gil_enabled()
        except TypeError:
            freethreaded = False
        if freethreaded:
            print(
                "Error: Python free-threaded (3.13t+) no es compatible "
                "con PyQt6. Usa `python -m azero` con un Python normal "
                "o el ejecutable compilado.",
                file=sys.stderr,
            )
            raise SystemExit(2)


if __name__ == "__main__":
    _check_python()
    from .app import main
    raise SystemExit(main())
