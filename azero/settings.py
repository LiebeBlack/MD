"""Persistencia de configuracion del launcher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from . import hardware, paths
from .constants import DEFAULT_MEMORY_MB
from .util import read_json, write_json

_INT_FIELDS = {
    "memory_mb", "cpu_cores", "resolution_width", "resolution_height",
    "render_distance", "max_fps", "particles",
}
_BOOL_FIELDS = {
    "auto_close", "show_all_versions", "auto_download_java", "gpu_accel",
    "vsync", "use_vbo", "fancy_graphics", "hw_defaults_applied",
}
_STR_FIELDS = {
    "username", "active_account", "version", "java_path",
    "extra_jvm_args", "server", "optifine_profile", "last_optifine",
    "game_priority", "gc_preset", "win_geometry",
}


def _sanitize(data: dict) -> dict:
    """Descarta valores con tipo incorrecto (p. ej. settings.json editado
    a mano o importado) para que nunca rompa el arranque."""
    clean = {}
    for key, value in data.items():
        if key in _INT_FIELDS:
            try:
                clean[key] = int(value)
            except (TypeError, ValueError):
                continue
        elif key in _BOOL_FIELDS:
            if isinstance(value, bool):
                clean[key] = value
            elif isinstance(value, str):
                clean[key] = value.strip().lower() in ("1", "true", "yes")
        elif key in _STR_FIELDS and isinstance(value, str):
            clean[key] = value
    return clean


@dataclass
class Settings:
    username: str = "Player"
    # "" / "offline" = perfil local; "ms:<uuid>" = cuenta Microsoft guardada.
    active_account: str = ""
    version: str = "1.15.2"
    memory_mb: int = DEFAULT_MEMORY_MB
    java_path: str = ""
    auto_close: bool = True
    show_all_versions: bool = False
    auto_download_java: bool = True
    extra_jvm_args: str = ""
    server: str = ""
    optifine_profile: str = ""
    last_optifine: str = ""
    # Uso de recursos del proceso del juego.
    game_priority: str = "normal"   # idle|below_normal|normal|above_normal|high
    cpu_cores: int = 0              # 0 = todos los nucleos
    gc_preset: str = "auto"         # auto|g1|serial|parallel
    # Aceleracion y video (Intel UHD / iGPU incluidos).
    gpu_accel: bool = True          # pipeline OpenGL para Java2D
    resolution_width: int = 0       # 0 = automaticamente
    resolution_height: int = 0
    render_distance: int = 0        # 0 = automatico, si no 2-32 chunks
    max_fps: int = 0                # 0 = auto, si no 30/60/120/144/240
    vsync: bool = True              # enableVsync en options.txt
    particles: int = -1             # -1 = auto, 0=todas 1=reducidas 2=minimas
    use_vbo: bool = True            # useVbo: renderizado por lotes en GPU
    fancy_graphics: bool = True     # fancyGraphics: sombras y detalles extra
    # True tras el ajuste unico de defaults segun el hardware detectado.
    hw_defaults_applied: bool = False
    # Geometria de la ventana (base64 de saveGeometry) para restaurarla.
    win_geometry: str = ""

    @classmethod
    def load(cls) -> "Settings":
        paths.ensure_dirs()
        raw = read_json(paths.SETTINGS_FILE, {}) or {}
        valid = {item.name for item in fields(cls)}
        data = {key: value for key, value in raw.items() if key in valid}
        data = _sanitize(data)
        settings = cls(**data)
        # Ajuste unico al hardware real en el primer arranque (equipo modesto:
        # menos RAM para el juego y GC de un solo hilo). Solo toca valores que
        # siguen en su default antiguo; una eleccion manual posterior se respeta.
        if not settings.hw_defaults_applied:
            recommended = hardware.recommended_memory_mb()
            if (settings.memory_mb == DEFAULT_MEMORY_MB
                    and recommended < settings.memory_mb):
                settings.memory_mb = recommended
            if settings.gc_preset == "auto" and hardware.cpu_cores() <= 4:
                settings.gc_preset = "serial"
            settings.hw_defaults_applied = True
            settings.save()
        return settings

    def save(self) -> None:
        paths.ensure_dirs()
        write_json(paths.SETTINGS_FILE, asdict(self))
