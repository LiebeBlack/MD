# AZeroCraft Launcher — notas para agentes

Launcher de Minecraft Java Edition (1.8–1.15.2) para Windows, escrito en
Python + PyQt6. Repositorio: https://github.com/LiebeBlack/MD

## Comandos

```powershell
# Tests unitarios (24 tests en tests/test_core.py)
.\.venv-build\Scripts\python.exe -m unittest discover -s tests

# Compilar todo el paquete (chequeo de sintaxis)
.\.venv-build\Scripts\python.exe -m compileall -q azero main.py

# Ejecutar en desarrollo (usar Python CON GIL, no free-threaded 3.13t+)
py -3.15 main.py
# o con el venv del build:
.\.venv-build\Scripts\python.exe main.py

# Build completo del ejecutable + instalador
.\build.ps1            # exe onedir en dist\AZeroCraft\
.\build.ps1 -Installer # ademas genera el instalador Inno Setup

# Verificar una version de Minecraft sin descargar el juego
.\.venv-build\Scripts\python.exe tools\verify_version.py 1.12.1
```

## Notas importantes

- **Python free-threaded (3.13t/3.15t) NO es compatible con PyQt6** —
  `main.py` y `azero/__main__.py` muestran un aviso y salen con codigo 2.
  Usar siempre el Python normal (`py -3.15`, no `py -3.15t`).
- Los datos del launcher viven en `data/` (o la carpeta elegida en el
  primer arranque / `AZEROCRAFT_DATA`). Nunca versionar `data/`.
- `azero/paths.py` deriva todas las rutas de `DATA_DIR`; usar
  `paths.X` en tiempo de llamada, nunca importar constantes sueltas.
- `Settings.load()` sanea tipos (`_sanitize`): los settings.json
  importados/editados a mano no deben romper el arranque.
- Las opciones de vídeo del juego se escriben en `options.txt` antes de
  cada lanzamiento (`launch.apply_video_options`) sin tocar otras claves.
- Los workers QThread se cancelan y esperan en `MainWindow.closeEvent`;
  cualquier QThread nuevo debe registrarse ahi para evitar crashes al
  cerrar.
- Minecraft 1.12.1 usa `minecraftArguments` (formato antiguo); las
  versiones 1.13+ usan `arguments.game/jvm` — `launch.build_command`
  maneja ambos y combina el tweakClass de OptiFine.
