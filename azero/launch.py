"""Construccion de la linea de comandos y arranque desacoplado del juego."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import java as java_module
from . import hardware, paths
from .auth import OfflineProfile, OnlineProfile
from . import msauth
from .constants import APP_NAME, APP_VERSION
from .install import PreparedGame, TaskContext, prepare
from .rules import default_features, expand_arguments

_PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

_STRUCTURAL_JVM = {"-cp", "-classpath"}

_GC_FLAGS = {
    "g1": ["-XX:+UseG1GC"],
    "serial": ["-XX:+UseSerialGC"],
    "parallel": ["-XX:+UseParallelGC"],
}

_PRIORITY_CLASSES = {
    "idle": 0x00000040,          # IDLE_PRIORITY_CLASS
    "below_normal": 0x00004000,  # BELOW_NORMAL_PRIORITY_CLASS
    "normal": 0x00000020,        # NORMAL_PRIORITY_CLASS
    "above_normal": 0x00008000,  # ABOVE_NORMAL_PRIORITY_CLASS
    "high": 0x00000080,          # HIGH_PRIORITY_CLASS
}


class LaunchError(RuntimeError):
    pass


@dataclass
class LaunchHandle:
    process: subprocess.Popen
    log_path: Path
    command: list[str]
    auto_close: bool
    log_handle: object = None


@dataclass
class LaunchOutcome:
    pid: int
    log_path: Path
    command: list[str]
    auto_close: bool


def _context(prepared: PreparedGame,
             profile: OfflineProfile | OnlineProfile) -> dict[str, str]:
    classpath = os.pathsep.join(str(item) for item in prepared.classpath)
    version_json = prepared.version_json
    index_name = version_json["assetIndex"]["id"]
    return {
        "auth_player_name": profile.name,
        "auth_uuid": profile.uuid,
        "auth_access_token": profile.access_token,
        "auth_session": f"token:{profile.access_token}:{profile.uuid}",
        "user_type": profile.user_type,
        "version_name": prepared.version_id,
        "version_type": version_json.get("type", "release"),
        "game_directory": str(prepared.game_dir),
        "assets_root": str(prepared.assets_dir),
        "game_assets": str(prepared.assets_dir / "virtual" / "legacy"),
        "assets_index_name": index_name,
        "user_properties": "{}",
        "natives_directory": str(prepared.natives_dir),
        "launcher_name": APP_NAME,
        "launcher_version": APP_VERSION,
        "classpath": classpath,
        "classpath_separator": os.pathsep,
        "library_directory": str(paths.LIBRARIES_DIR),
        "main_class": prepared.main_class,
        "resolution_width": "854",
        "resolution_height": "480",
        "clientid": "",
        "auth_xuid": "",
    }


def _substitute(value: str, context: dict[str, str]) -> str:
    return _PLACEHOLDER.sub(lambda match: context.get(match.group(1), ""), value)


def _quick_connect(settings) -> list[str]:
    server = (settings.server or "").strip()
    if not server:
        return []
    host, port = server, "25565"
    if server.startswith("["):
        # IPv6 con corchetes: [::1]:25565
        end = server.find("]")
        if end > 0:
            host = server[1:end]
            rest = server[end + 1:]
            if rest.startswith(":") and rest[1:].isdigit():
                port = rest[1:]
    elif server.count(":") == 1:
        candidate_host, candidate_port = server.rsplit(":", 1)
        if candidate_port.isdigit():
            host, port = candidate_host, candidate_port
    if not host:
        return []
    return ["--server", host, "--port", port]


def build_command(prepared: PreparedGame,
                  profile: OfflineProfile | OnlineProfile, settings,
                  runtime: java_module.JavaRuntime) -> list[str]:
    context = _context(prepared, profile)
    version_json = prepared.version_json
    features = default_features()
    memory = max(1024, int(settings.memory_mb))

    jvm: list[str] = [f"-Xms{min(memory, 1024)}M", f"-Xmx{memory}M"]

    version_jvm = []
    if version_json.get("arguments"):
        version_jvm = expand_arguments(version_json["arguments"].get("jvm", []), features)
    classpath_value = context["classpath"]
    for raw in version_jvm:
        if raw in _STRUCTURAL_JVM:
            continue
        value = _substitute(raw, context)
        # Los manifiestos 1.13+ repiten -cp/${classpath}/${main_class} en
        # arguments.jvm; el launcher ya los añade al final por su cuenta.
        if not value or value in (classpath_value, prepared.main_class):
            continue
        if value.startswith(("-Djava.library.path=", "-Dminecraft.launcher.brand=",
                             "-Dminecraft.launcher.version=")):
            continue
        jvm.append(value)

    jvm.extend([
        f"-Djava.library.path={prepared.natives_dir}",
        f"-Dminecraft.launcher.brand={APP_NAME}",
        f"-Dminecraft.launcher.version={APP_VERSION}",
    ])
    if prepared.logging_path and prepared.logging_path.exists():
        jvm.append(f"-Dlog4j.configurationFile={prepared.logging_path}")

    jvm.extend(_GC_FLAGS.get(getattr(settings, "gc_preset", "auto"), []))

    # Aceleracion por GPU: pipeline OpenGL de Java2D (util en iGPU Intel UHD
    # y drivers antiguos donde D3D falla o es mas lento).
    if getattr(settings, "gpu_accel", True):
        jvm.append("-Dsun.java2d.opengl=true")

    extra = (settings.extra_jvm_args or "").strip()
    if extra:
        jvm.extend(shlex.split(extra, posix=False))

    jvm.extend(["-cp", classpath_value, prepared.main_class])

    # Versiones antiguas usan minecraftArguments (string); las nuevas usan
    # arguments.game (lista con reglas). OptiFine anade arguments.game encima
    # de un perfil heredado con minecraftArguments: hay que combinar ambos.
    game: list[str] = []
    if version_json.get("minecraftArguments"):
        game.extend(version_json["minecraftArguments"].split())
    game.extend(expand_arguments(
        (version_json.get("arguments") or {}).get("game", []), features
    ))
    game_args = [arg for arg in (_substitute(item, context) for item in game)
                 if arg]
    game_args.extend(_quick_connect(settings))

    return [str(runtime.java), *jvm, *game_args]


def apply_video_options(game_dir: Path, settings) -> None:
    """Aplica resolucion y distancia de renderizado en options.txt.

    Solo escribe las claves configuradas en el launcher; el resto del
    archivo del usuario se conserva intacto. Nunca debe romper el arranque.
    """
    updates: dict[str, str] = {}
    width = int(getattr(settings, "resolution_width", 0) or 0)
    height = int(getattr(settings, "resolution_height", 0) or 0)
    if width > 0 and height > 0:
        updates["overrideWidth"] = str(width)
        updates["overrideHeight"] = str(height)
    distance = int(getattr(settings, "render_distance", 0) or 0)
    if 2 <= distance <= 32:
        updates["renderDistance"] = str(distance)
    max_fps = int(getattr(settings, "max_fps", 0) or 0)
    if max_fps > 0:
        updates["maxFps"] = str(max_fps)
    particles = int(getattr(settings, "particles", -1))
    if particles in (0, 1, 2):
        updates["particles"] = str(particles)
    # VSync y VBO siempre se escriben: son toggles del launcher y sus
    # defaults coinciden con los del juego, asi que no hay sorpresa.
    updates["enableVsync"] = (
        "true" if getattr(settings, "vsync", True) else "false")
    updates["useVbo"] = (
        "true" if getattr(settings, "use_vbo", True) else "false")
    updates["fancyGraphics"] = (
        "true" if getattr(settings, "fancy_graphics", True) else "false")
    if not updates:
        return

    try:
        options = game_dir / "options.txt"
        lines = options.read_text(encoding="utf-8",
                                  errors="replace").splitlines() \
            if options.exists() else []
        seen = set()
        out = []
        for line in lines:
            key = line.split(":", 1)[0].strip()
            if key in updates:
                out.append(f"{key}:{updates[key]}")
                seen.add(key)
            else:
                out.append(line)
        for key, value in updates.items():
            if key not in seen:
                out.append(f"{key}:{value}")
        options.write_text("\n".join(out) + "\n", encoding="utf-8")
    except OSError:
        pass


def tail_log(path: Path, lines: int = 25) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])


def _apply_process_tuning(process: subprocess.Popen, settings) -> None:
    """Aplica prioridad y afinidad de CPU al proceso del juego.

    Nunca debe impedir el arranque: cualquier fallo se ignora en silencio.
    """
    priority = getattr(settings, "game_priority", "normal")
    cores = int(getattr(settings, "cpu_cores", 0) or 0)
    try:
        if sys.platform.startswith("win"):
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.OpenProcess.restype = wintypes.HANDLE
            kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                             wintypes.DWORD]
            kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE,
                                                  wintypes.DWORD]
            kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE,
                                                        ctypes.c_size_t]
            kernel32.SetProcessAffinityMask.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

            # PROCESS_SET_INFORMATION (0x0200) | PROCESS_SET_QUOTA (0x0100)
            handle = kernel32.OpenProcess(0x0300, False, process.pid)
            if not handle:
                return
            try:
                if priority in _PRIORITY_CLASSES:
                    kernel32.SetPriorityClass(handle,
                                              _PRIORITY_CLASSES[priority])
                if cores > 0:
                    total = os.cpu_count() or cores
                    bits = min(cores, total)
                    mask = (1 << bits) - 1
                    kernel32.SetProcessAffinityMask(handle, mask)
            finally:
                kernel32.CloseHandle(handle)
        else:
            if cores > 0 and hasattr(os, "sched_setaffinity"):
                allowed = sorted(os.sched_getaffinity(0))
                count = min(cores, len(allowed))
                os.sched_setaffinity(process.pid, set(allowed[:count]))
            if priority in ("idle", "below_normal") and hasattr(os, "nice"):
                os.nice(5 if priority == "idle" else 3)
    except (OSError, AttributeError, ValueError):
        pass


def spawn(command: list[str], cwd: Path, auto_close: bool,
          settings=None) -> LaunchHandle:
    paths.ensure_dirs()
    log_path = paths.LOGS_DIR / f"game-{time.strftime('%Y%m%d-%H%M%S')}.log"
    log_handle = log_path.open("wb")

    flags = 0
    if sys.platform.startswith("win"):
        flags = CREATE_NO_WINDOW
        if auto_close:
            # Proceso independiente: sobrevive al cierre inmediato del launcher.
            flags |= DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=flags,
            close_fds=True,
        )
    except OSError as error:
        log_handle.close()
        raise LaunchError(f"No se pudo iniciar el juego: {error}") from error

    if settings is not None:
        _apply_process_tuning(process, settings)

    return LaunchHandle(process=process, log_path=log_path, command=command,
                        auto_close=auto_close, log_handle=log_handle)


def install_and_launch(version_id: str, settings, ctx: TaskContext,
                       with_assets: bool = True,
                       on_spawned=None) -> LaunchOutcome:
    if (getattr(settings, "active_account", "") or "").startswith("ms:"):
        ctx.stage("Verificando sesion de Microsoft")
    profile = msauth.resolve_profile(settings)

    prepared = prepare(version_id, ctx, with_assets=with_assets)
    ctx.stage(f"Preparando Java {prepared.java_major}")
    runtime = java_module.ensure_java(
        prepared.java_major,
        java_path=settings.java_path,
        allow_download=settings.auto_download_java,
        progress=ctx.progress,
        stage=ctx.stage,
        log=ctx.log,
        cancel=ctx.cancel_event.is_set,
    )
    ctx.log(f"Usando {runtime.label} desde {runtime.home}")
    ctx.check()

    ctx.stage("Construyendo linea de comandos")
    command = build_command(prepared, profile, settings, runtime)
    ctx.log(f"Lanzando {version_id} como {profile.name} (UUID {profile.uuid})")
    ctx.log(f"Hardware: {hardware.summary()}")
    apply_video_options(prepared.game_dir, settings)

    handle = spawn(command, prepared.game_dir, bool(settings.auto_close),
                   settings)
    if on_spawned is not None:
        on_spawned(handle)
    ctx.stage("Iniciando Minecraft")

    if handle.auto_close:
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline:
            code = handle.process.poll()
            if code is not None:
                tail = tail_log(handle.log_path)
                handle.log_handle.close()
                raise LaunchError(
                    f"Minecraft termino al iniciar (codigo {code}).\n{tail}"
                )
            time.sleep(0.25)
        ctx.progress(1, 1)
        ctx.stage("Juego lanzado")
        ctx.log("El launcher se cerrara para liberar recursos.")
    return LaunchOutcome(
        pid=handle.process.pid,
        log_path=handle.log_path,
        command=handle.command,
        auto_close=handle.auto_close,
    )
