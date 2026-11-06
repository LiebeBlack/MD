"""Evaluacion de las reglas de los manifiestos de Minecraft."""

from __future__ import annotations

import platform
import re
import sys
from typing import Iterable

_ARCH_ALIASES = {
    "amd64": "x86_64",
    "x86_64": "x86_64",
    "x64": "x86_64",
    "i386": "x86",
    "i686": "x86",
    "x86": "x86",
    "arm64": "arm64",
    "aarch64": "arm64",
}


def os_name() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "osx"
    return "linux"


def os_arch() -> str:
    return _ARCH_ALIASES.get(platform.machine().lower(), platform.machine().lower())


def os_version() -> str:
    return platform.version() or ""


def default_features() -> dict[str, bool]:
    return {
        "is_demo_user": False,
        "has_custom_resolution": False,
        "has_quick_plays_support": False,
        "is_quick_play_singleplayer": False,
        "is_quick_play_multiplayer": False,
        "is_quick_play_realms": False,
    }


def _version_tuple(text: str) -> tuple[int, ...]:
    """'10.0.17134' -> (10, 0, 17134); tolera componentes no numericos."""
    parts = []
    for piece in str(text).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _rule_matches(rule: dict, features: dict[str, bool]) -> bool:
    os_rule = rule.get("os")
    if os_rule:
        if "name" in os_rule and os_rule["name"] != os_name():
            return False
        if "arch" in os_rule and os_rule["arch"] != os_arch():
            return False
        if "version" in os_rule:
            try:
                if not re.search(os_rule["version"], os_version()):
                    return False
            except re.error:
                return False
        version_range = os_rule.get("versionRange")
        if version_range:
            current = _version_tuple(os_version())
            minimum = version_range.get("min")
            maximum = version_range.get("max")
            if minimum and current < _version_tuple(minimum):
                return False
            if maximum and current > _version_tuple(maximum):
                return False

    rule_features = rule.get("features")
    if rule_features:
        for key, expected in rule_features.items():
            if bool(features.get(key, False)) != bool(expected):
                return False
    return True


def rules_allow(rules: Iterable[dict] | None, features: dict[str, bool] | None = None) -> bool:
    if not rules:
        return True
    features = features or default_features()
    allowed = False
    for rule in rules:
        if _rule_matches(rule, features):
            allowed = rule.get("action") == "allow"
    return allowed


def expand_arguments(arguments: Iterable, features: dict[str, bool] | None = None) -> list[str]:
    """Aplana la lista de argumentos con reglas de los manifiestos 1.13+."""
    features = features or default_features()
    result: list[str] = []
    for entry in arguments:
        if isinstance(entry, str):
            result.append(entry)
            continue
        if not isinstance(entry, dict):
            continue
        if not rules_allow(entry.get("rules"), features):
            continue
        value = entry.get("value", [])
        if isinstance(value, str):
            result.append(value)
        else:
            result.extend(str(item) for item in value)
    return result
