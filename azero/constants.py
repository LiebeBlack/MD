"""Constantes globales del launcher."""

from __future__ import annotations

APP_NAME = "AZeroCraft"
APP_VERSION = "1.0.0"
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (Minecraft Java Launcher)"

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES_URL = "https://resources.download.minecraft.net"
LIBRARIES_URL = "https://libraries.minecraft.net/"
ADOPTIUM_ASSET_URL = (
    "https://api.adoptium.net/v3/assets/latest/{major}/hotspot"
    "?architecture={arch}&image_type=jre&os={os}&vendor=eclipse"
)

# Rango objetivo del launcher (1.8 -> 1.15.2).
MIN_VERSION = (1, 8, 0)
MAX_VERSION = (1, 15, 999)

DEFAULT_MEMORY_MB = 2048
MIN_MEMORY_MB = 1024
MAX_MEMORY_MB = 16384
MEMORY_STEP_MB = 512

# Versiones de Minecraft que se ejecutan correctamente con Java 8.
LEGACY_JAVA_MAX_VERSION = (1, 16, 5)
