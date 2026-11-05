"""Perfiles offline con UUID determinista (igual que Java)."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,16}$")


@dataclass(frozen=True)
class OfflineProfile:
    name: str
    uuid: str
    access_token: str = "0"
    user_type: str = "legacy"

    @property
    def uuid_dashed(self) -> str:
        return self.uuid

    @property
    def initials(self) -> str:
        return self.name[:2].upper() if self.name else "?"


def offline_uuid(name: str) -> str:
    """Reproduce UUID.nameUUIDFromBytes("OfflinePlayer:" + nombre) de Java."""
    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # variante IETF
    return str(uuid.UUID(bytes=bytes(digest)))


def validate_username(name: str) -> str | None:
    """Devuelve un mensaje de error o None si el nombre es valido."""
    if not name:
        return "Escribe un nombre de jugador."
    if not USERNAME_RE.match(name):
        return "Usa de 3 a 16 caracteres: letras, numeros o guion bajo."
    return None


def create_profile(name: str) -> OfflineProfile:
    return OfflineProfile(name=name, uuid=offline_uuid(name))
