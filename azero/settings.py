"""Persistencia de configuracion del launcher."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields

from .constants import DEFAULT_MEMORY_MB
from .paths import SETTINGS_FILE, ensure_dirs
from .util import read_json, write_json


@dataclass
class Settings:
    username: str = "Player"
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

    @classmethod
    def load(cls) -> "Settings":
        ensure_dirs()
        raw = read_json(SETTINGS_FILE, {}) or {}
        valid = {item.name for item in fields(cls)}
        data = {key: value for key, value in raw.items() if key in valid}
        return cls(**data)

    def save(self) -> None:
        ensure_dirs()
        write_json(SETTINGS_FILE, asdict(self))
