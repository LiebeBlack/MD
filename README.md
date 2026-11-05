# AZeroCraft Launcher

**Desarrollado por [Liebe Black](https://github.com/LiebeBlack)** ·
Repositorio: [github.com/LiebeBlack/MD](https://github.com/LiebeBlack/MD)

> Documentación web del proyecto en [`docs/index.html`](docs/index.html)
> (publicable gratis en GitHub Pages desde la carpeta `/docs`).

Launcher ligero para Minecraft Java Edition (1.8 – 1.15.2) con soporte de
OptiFine, modo offline, Java automático (Temurin) y ajustes de rendimiento.

## Características

- Descarga e instalación completa de cualquier versión del manifiesto oficial
  de Mojang: cliente, librerías, nativos y assets (con verificación SHA-1/SHA-256).
- Java automático: detecta JREs instalados y descarga Temurin (Adoptium) si falta
  la versión requerida.
- OptiFine: instala el parche oficial sin GUI y crea un perfil propio.
- Mods: gestor de `.jar` en Ajustes → Mods. Permite añadir varios mods a la
  vez (p. ej. `VanillaFix-1.0.10-150.jar`), listar con nombre/versión
  detectados (`mcmod.info`, `fabric.mod.json`), quitarlos y abrir la carpeta.
  Si el mod es de Forge y no hay loader, el launcher ofrece instalarlo
  automáticamente. Botón "Instalar Forge…": descarga el instalador oficial
  y crea el perfil **sin abrir ventanas** (extrayendo `install_profile.json`);
  su perfil aparece en Versiones agrupado por versión y carga los mods al
  jugar.
- Modo offline con UUID v3 determinista (compatible con `nameUUIDFromBytes`).
- Control de recursos: memoria RAM, prioridad de proceso, afinidad de CPU y
  recolector de basura (GC).
- Interfaz con navegación lateral y páginas: Jugar, Versiones (gestor de
  archivos instalados), Cuenta e Historial, Ajustes y Acerca de.
- Ajustes de vídeo completos (se escriben en `options.txt` antes de cada
  lanzamiento): resolución personalizada, distancia de renderizado, FPS
  máximo, VSync, partículas, VBO, gráficos Fancy y aceleración GPU OpenGL,
  además de presets de un clic (Rendimiento/Equilibrado/Calidad) y un
  botón "Optimizar para este equipo" que adapta los ajustes al hardware
  detectado (CPU, núcleos, RAM, flags SSE4.2/AVX).
- RAM previsualizada en MB exactos con presets rápidos (2/4 GB,
  recomendado, máximo según el equipo).
- Cuentas: perfil offline con nombre personalizado o cuenta Microsoft
  (device code) para servidores oficiales online-mode. Todo el contenido
  es gratuito y funciona sin cuenta.
- Historial persistente de descargas, sesiones y registros en
  `data/launcher.db` (SQLite).
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

Los assets quedan publicados en
[Releases](https://github.com/LiebeBlack/MD/releases).

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
  msauth.py           # cuenta Microsoft (device code → Minecraft Services)
  database.py         # SQLite: historial, sesiones y cuentas
  ui/                 # PyQt6: ventana, páginas, tema, widgets
installer/setup.iss   # script de Inno Setup
packaging/            # icono y scripts de build
azero.spec            # spec de PyInstaller
tools/verify_version.py
tests/
```

## Aviso legal

AZeroCraft Launcher es un proyecto independiente de **Liebe Black**. No está
afilado a Mojang AB ni Microsoft. El software se distribuye bajo fair use:
no incluye ni redistribuye archivos del juego, que se descargan en tiempo de
ejecución desde los servidores oficiales. Para servidores online o Realms se
requiere una cuenta oficial de Minecraft. El software se ofrece "tal cual",
sin garantías. Consulta los términos completos en
[`installer/license.txt`](installer/license.txt).

## Notas

- Las versiones 1.8–1.12 usan el formato `minecraftArguments`; 1.13+ usa
  `arguments` con reglas. Ambos formatos (y sus combinaciones, p. ej.
  OptiFine sobre 1.12.x) están soportados.
- El juego se lanza como proceso independiente: el launcher puede cerrarse
  tras el arranque y liberarse por completo de memoria.
