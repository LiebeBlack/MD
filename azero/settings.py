"""Persistencia de configuracion del launcher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from . import hardware, paths
from .constants import DEFAULT_MEMORY_MB
from .util import read_json, write_json

_INT_FIELDS = {
    "memory_mb", "cpu_cores",
}
_BOOL_FIELDS = {
    "auto_close", "show_all_versions", "auto_download_java", "gpu_accel",
    "hw_defaults_applied",
}
_STR_FIELDS = {
    "username", "active_account", "version", "java_path",
    "extra_jvm_args", "server", "optifine_profile", "last_optifine",
    "game_priority", "gc_preset", "win_geometry", "ui_theme",
    "extra_mc_dirs",
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
    # Aceleracion del proceso del juego (Intel UHD / iGPU incluidos).
    gpu_accel: bool = True          # pipeline OpenGL para Java2D
    # True tras el ajuste unico de defaults segun el hardware detectado.
    hw_defaults_applied: bool = False
    # Geometria de la ventana (base64 de saveGeometry) para restaurarla.
    win_geometry: str = ""
    # Tema de la interfaz: "light" (Office claro) u "dark" (Office oscuro).
    ui_theme: str = "light"
    # Raices .minecraft adicionales detectadas por el escaner (una por
    # linea). Sus perfiles de version se reconocen junto a los oficiales.
    extra_mc_dirs: str = ""

    @classmethod
    def load(cls) -> "Settings":
        paths.ensure_dirs()
        raw = read_json(paths.SETTINGS_FILE, {}) or {}
        valid = {item.name for item in fields(cls)}
        data = {key: value for key, value in raw.items() if key in valid}
        data = _sanitize(data)
        settings = cls(**data)
        if settings.ui_theme not in ("light", "dark"):
            settings.ui_theme = "light"
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
