# AZeroCraft Launcher

Launcher ligero para Minecraft Java Edition (1.8 – 1.15.2) con soporte de
OptiFine, modo offline, Java automático (Temurin) y ajustes de rendimiento.

## Características

- Descarga e instalación completa de cualquier versión del manifiesto oficial
  de Mojang: cliente, librerías, nativos y assets (con verificación SHA-1/SHA-256).
- Java automático: detecta JREs instalados y descarga Temurin (Adoptium) si falta
  la versión requerida.
- OptiFine: instala el parche oficial sin GUI y crea un perfil propio.
- Modo offline con UUID v3 determinista (compatible con `nameUUIDFromBytes`).
- Control de recursos: memoria RAM, prioridad de proceso, afinidad de CPU y
  recolector de basura (GC).
- Conexión rápida a servidor (`host:puerto`) y argumentos JVM extra.
- Portable por defecto: todos los datos en `./data` (o `%APPDATA%\AZeroCraft`
  cuando está instalado en Program Files). Se puede reubicar con la variable
  de entorno `AZEROCRAFT_DATA`.

## Requisitos

- Windows 10/11 (probado en Windows 11; el código también contempla Linux/macOS
  en el núcleo, la UI está pensada para Windows).
- Python 3.11+ para desarrollo, o el ejecutable/instalador compilado.

## Uso en desarrollo

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py            # o: python -m azero
```

## Tests y verificación

```powershell
python -m unittest discover -s tests -v
python tools\verify_version.py 1.12.1   # QA completo sin descargar el juego
```

`verify_version.py` resuelve manifiesto → perfil → librerías → nativos →
assets → línea de comandos y comprueba por HTTP que todas las URLs de
descarga responden.

## Compilar para producción

```powershell
.\build.ps1              # genera dist\AZeroCraft\AZeroCraft.exe
.\build.ps1 -Installer   # además genera dist\AZeroCraft-Setup-1.0.0.exe (requiere Inno Setup 6)
```

También se puede compilar el instalador directamente con Inno Setup:

```powershell
ISCC installer\setup.iss
```

El instalador es por usuario (no requiere admin), se instala en
`%LOCALAPPDATA%\Programs\AZeroCraft` y crea accesos directos en el menú
Inicio y, opcionalmente, en el escritorio.

## Publicar en GitHub Releases

El workflow `.github/workflows/release.yml` compila todo automáticamente
en Windows al hacer push de un tag `v*`:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

El workflow genera y publica como assets del release:

- `AZeroCraft-Setup-1.0.0.exe` — instalador Inno Setup.
- `AZeroCraft-windows-x64.zip` — carpeta portable completa
  (`dist\AZeroCraft\` con el exe y todos los DLL de Qt/Python).

También puede ejecutarse manualmente desde la pestaña *Actions* → *Release*.

> Nota: para generar el instalador localmente se necesita [Inno Setup 6](https://jrsoftware.org/isinfo.php).

## Estructura

```
main.py               # entry point
azero/                # núcleo + UI
  app.py              # arranque de la aplicación
  paths.py            # rutas de datos (portable / %APPDATA%)
  manifest.py         # manifiestos oficiales y herencia de perfiles
  install.py          # descarga e instalación de versiones
  libraries.py        # classpath, reglas y nativos
  assets.py           # índice y objetos de assets
  java.py             # detección y descarga de Java (Temurin)
  launch.py           # línea de comandos, spawn y tuning de proceso
  optifine.py         # instalación de OptiFine headless
  ui/                 # PyQt6: ventana, tema, widgets
installer/setup.iss   # script de Inno Setup
packaging/            # icono y scripts de build
azero.spec            # spec de PyInstaller
tools/verify_version.py
tests/
```

## Notas

- Las versiones 1.8–1.12 usan el formato `minecraftArguments`; 1.13+ usa
  `arguments` con reglas. Ambos formatos (y sus combinaciones, p. ej.
  OptiFine sobre 1.12.x) están soportados.
- El juego se lanza como proceso independiente: el launcher puede cerrarse
  tras el arranque y liberarse por completo de memoria.
