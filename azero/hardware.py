"""Deteccion de hardware: CPU, nucleos, RAM y flags de instruccion.

No requiere AVX ni ninguna ISA concreta: Minecraft 1.8-1.15.2 funciona en
cualquier x86-64 con SSE2. Los flags se usan solo con fines informativos
y de sugerencia de configuracion.
"""

from __future__ import annotations

import os
import platform
import sys
from ctypes import byref, c_ulong, c_ulonglong, sizeof, Structure

if sys.platform.startswith("win"):
    from ctypes import windll
else:
    windll = None  # type: ignore[assignment]


class _MemoryStatus(Structure):
    _fields_ = [
        ("dwLength", c_ulong),
        ("dwMemoryLoad", c_ulong),
        ("ullTotalPhys", c_ulonglong),
        ("ullAvailPhys", c_ulonglong),
        ("ullTotalPageFile", c_ulonglong),
        ("ullAvailPageFile", c_ulonglong),
        ("ullTotalVirtual", c_ulonglong),
        ("ullAvailVirtual", c_ulonglong),
        ("ullAvailExtendedVirtual", c_ulonglong),
    ]


def cpu_name() -> str:
    """Nombre comercial del procesador."""
    if sys.platform.startswith("win"):
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                return str(value).strip()
        except OSError:
            pass
    name = platform.processor() or ""
    return name.strip() or platform.machine()


def cpu_cores() -> int:
    """Nucleos logicos disponibles para el proceso."""
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def ram_mb() -> int:
    """RAM fisica total en MiB."""
    if windll is not None:
        try:
            status = _MemoryStatus()
            status.dwLength = sizeof(status)
            if windll.kernel32.GlobalMemoryStatusEx(byref(status)):
                return int(status.ullTotalPhys // (1024 * 1024))
        except (OSError, AttributeError):
            pass
    try:
        return int(os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
                   // (1024 * 1024))
    except (ValueError, OSError, AttributeError):
        return 0


def cpu_flags() -> dict[str, bool]:
    """Flags de instruccion detectados (sse3, sse4_1, sse4_2, avx, avx2).

    En Linux se leen de /proc/cpuinfo. En Windows solo SSE2 es consultable
    de forma fiable via IsProcessorFeaturePresent; el resto queda en False
    (Minecraft 1.8-1.15.2 no los necesita: el minimo real es SSE2/x86-64).
    """
    # Constantes PROCESSOR_FEATURE_NUMBER (Windows 10+):
    # SSE3=13, SSSE3=36, SSE4.1=37, SSE4.2=38, AVX=39, AVX2=40, AVX512F=41.
    # En Windows antiguos la llamada devuelve 0 para las no soportadas.
    feature_map = {
        "sse2": 10,    # PF_XMMI64_INSTRUCTIONS_AVAILABLE (SSE2 en x64)
        "sse3": 13,    # PF_SSE3_INSTRUCTIONS_AVAILABLE
        "ssse3": 36,   # PF_SSSE3_INSTRUCTIONS_AVAILABLE
        "sse4_1": 37,  # PF_SSE4_1_INSTRUCTIONS_AVAILABLE
        "sse4_2": 38,  # PF_SSE4_2_INSTRUCTIONS_AVAILABLE
        "avx": 39,     # PF_AVX_INSTRUCTIONS_AVAILABLE
        "avx2": 40,    # PF_AVX2_INSTRUCTIONS_AVAILABLE
        "avx512f": 41, # PF_AVX512F_INSTRUCTIONS_AVAILABLE
    }
    flags = {"sse2": True, "sse3": False, "ssse3": False, "sse4_1": False,
             "sse4_2": False, "avx": False, "avx2": False, "avx512f": False}
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8",
                      errors="ignore") as handle:
                found = set(handle.read().replace("\t", " ").split())
            aliases = {"sse3": ("sse3", "pni"), "ssse3": ("ssse3",),
                       "sse4_1": ("sse4_1",), "sse4_2": ("sse4_2",),
                       "avx": ("avx",), "avx2": ("avx2",),
                       "sse2": ("sse2",), "avx512f": ("avx512f",)}
            for key, names in aliases.items():
                flags[key] = any(name in found for name in names)
            return flags
        except OSError:
            pass
    if windll is not None:
        try:
            is_present = windll.kernel32.IsProcessorFeaturePresent
            for key, feature in feature_map.items():
                flags[key] = bool(is_present(feature))
        except (OSError, AttributeError):
            pass
    return flags


def supported_flags_text() -> str:
    """Texto corto con los flags detectados, p. ej. 'SSE4.2 · AVX2'."""
    flags = cpu_flags()
    order = (("sse2", "SSE2"), ("sse3", "SSE3"), ("ssse3", "SSSE3"),
             ("sse4_1", "SSE4.1"), ("sse4_2", "SSE4.2"), ("avx", "AVX"),
             ("avx2", "AVX2"), ("avx512f", "AVX512F"))
    return " · ".join(label for key, label in order if flags.get(key)) or "SSE2"


def recommended_memory_mb(ram_total_mb: int | None = None) -> int:
    """Memoria sugerida para Minecraft: ~25% de la RAM, entre 2 y 8 GB."""
    total = ram_total_mb or ram_mb()
    if total <= 0:
        return 2048
    return max(2048, min(8192, int(total * 0.25 // 512) * 512))


def summary() -> str:
    """Resumen legible del hardware para mostrar en Ajustes."""
    parts = [cpu_name(), f"{cpu_cores()} nucleos"]
    total = ram_mb()
    if total:
        parts.append(f"{total / 1024:.0f} GB RAM")
    parts.append(supported_flags_text())
    return " · ".join(parts)
