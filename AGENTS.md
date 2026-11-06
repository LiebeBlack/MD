# AZeroCraft Launcher — notas para agentes

Launcher de Minecraft Java Edition (1.7 hasta la versión más reciente,
versionado de calendario 26.x) para Windows, escrito en
Python + PyQt6. Repositorio: https://github.com/LiebeBlack/MD

## Comandos

```powershell
# Tests unitarios (23 tests en tests/test_core.py)
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
- `paths.MC_DIR` apunta SIEMPRE a la carpeta `.minecraft` oficial
  (`%APPDATA%\.minecraft`) para compatibilidad con el launcher de Mojang:
  versiones, mundos, options.txt, resourcepacks, shaderpacks y mods se
  comparten. `DATA_DIR` solo guarda ajustes, cache, Java y logs propios.
- `azero/paths.py` deriva todas las rutas de `DATA_DIR`; usar
  `paths.X` en tiempo de llamada, nunca importar constantes sueltas.
- `Settings.load()` sanea tipos (`_sanitize`): los settings.json
  importados/editados a mano no deben romper el arranque.
- El launcher NO escribe `options.txt`: los ajustes de video se
  descontinuaron; las opciones del juego se gestionan dentro de Minecraft.
- Los workers QThread se cancelan y esperan en `MainWindow.closeEvent`;
  cualquier QThread nuevo debe registrarse ahi para evitar crashes al
  cerrar.
- Minecraft 1.12.1 y anteriores usan `minecraftArguments` (formato
  antiguo); 1.13+ usa `arguments.game/jvm` y 26.x añade
  `arguments.default-user-jvm` — `launch.build_command` maneja los tres
  y combina el tweakClass de OptiFine. Las librerías `:natives-*`
  (LWJGL3) van al classpath y se extraen en runtime; los nativos
  clasicos (`natives` map / `natives-windows` pre-1.16) se extraen a
  `natives/<version>/`.
- El selector de versiones es `ui.widgets.VersionPicker` (arbol
  familias → versiones base → perfiles OptiFine/Forge en un popup con
  buscador); `main_window._on_manifest_ready` lo alimenta y la
  seleccion se persiste en `settings.version`.
