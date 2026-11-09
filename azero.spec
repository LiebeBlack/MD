# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para AZeroCraft Launcher (onedir, sin consola)."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()
ICON = ROOT / "assets" / "azero.ico"

# La version del ejecutable se lee de azero/constants.py para que el
# binario nunca quede desincronizado de APP_VERSION.
import re

_const = (ROOT / "azero" / "constants.py").read_text(encoding="utf-8")
_match = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', _const, re.M)
if not _match:
    raise SystemExit("No se encontro APP_VERSION en azero/constants.py")
VERSION = _match.group(1)
_VER_TUPLE = tuple(int(p) for p in VERSION.split("."))
while len(_VER_TUPLE) < 4:
    _VER_TUPLE += (0,)

from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo,
                                                 StringStruct, StringTable,
                                                 VarFileInfo, VarStruct,
                                                 VSVersionInfo)

block_cipher = None

# Metadatos del ejecutable (propiedades del archivo en Windows).
file_version = f"{VERSION}.0"
prod_version = VERSION
verinfo = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=_VER_TUPLE[:4], prodvers=_VER_TUPLE[:4],
        mask=0x3F, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo([StringTable(
            "040904B0",
            [StringStruct("CompanyName", "Liebe Black"),
             StringStruct("FileDescription", "AZeroCraft Launcher"),
             StringStruct("FileVersion", file_version),
             StringStruct("InternalName", "AZeroCraft"),
             StringStruct("LegalCopyright", "Copyright (C) 2026 Liebe Black"),
             StringStruct("OriginalFilename", "AZeroCraft.exe"),
             StringStruct("ProductName", "AZeroCraft Launcher"),
             StringStruct("ProductVersion", prod_version)])]),
        VarFileInfo([VarStruct("Translation", [1033, 1200])]),
    ],
)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "unittest"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AZeroCraft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.exists() else None,
    version=verinfo,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AZeroCraft",
)
