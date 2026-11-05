"""Persistencia de configuracion del launcher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from . import paths
from .constants import DEFAULT_MEMORY_MB
from .util import read_json, write_json


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

    @classmethod
    def load(cls) -> "Settings":
        paths.ensure_dirs()
        raw = read_json(paths.SETTINGS_FILE, {}) or {}
        valid = {item.name for item in fields(cls)}
        data = {key: value for key, value in raw.items() if key in valid}
        return cls(**data)

    def save(self) -> None:
        paths.ensure_dirs()
        write_json(paths.SETTINGS_FILE, asdict(self))
