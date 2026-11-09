"""Constantes globales del launcher."""

from __future__ import annotations

APP_NAME = "AZeroCraft"
APP_VERSION = "4.37.58"
USER_AGENT = f"{APP_NAME}/{APP_VERSION} (Minecraft Java Launcher)"

VERSION_MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
RESOURCES_URL = "https://resources.download.minecraft.net"
LIBRARIES_URL = "https://libraries.minecraft.net/"
# Microsoft Build of OpenJDK: URLs oficiales por major LTS
# (https://learn.microsoft.com/java/openjdk/download-major-urls).
MICROSOFT_JDK_URL = ("https://aka.ms/download-jdk/"
                     "microsoft-jdk-{major}-{platform}")

# Rango objetivo del launcher (1.7 -> ultima version publicada; Mojang
# usa versionado de calendario desde la 26.x, p. ej. 26.3).
MIN_VERSION = (1, 7, 0)
MAX_VERSION = (999, 99, 999)

DEFAULT_MEMORY_MB = 2048
MIN_MEMORY_MB = 1024
MAX_MEMORY_MB = 16384
MEMORY_STEP_MB = 256

# Repositorio y enlaces del proyecto.
REPO_URL = "https://github.com/LiebeBlack/MD"
RELEASES_URL = f"{REPO_URL}/releases"
LATEST_RELEASE_API = ("https://api.github.com/repos/LiebeBlack/MD"
                      "/releases/latest")
ISSUES_URL = f"{REPO_URL}/issues"
SPONSORS_URL = "https://github.com/sponsors/LiebeBlack"
DOCS_URL = f"{REPO_URL}/blob/main/docs/index.html"
