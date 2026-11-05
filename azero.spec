# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para AZeroCraft Launcher (onedir, sin consola)."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve()
ICON = ROOT / "assets" / "azero.ico"

from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo,
                                                 StringStruct, StringTable,
                                                 VarFileInfo, VarStruct,
                                                 VSVersionInfo)

block_cipher = None

# Metadatos del ejecutable (propiedades del archivo en Windows).
file_version = "1.0.0.0"
prod_version = "1.0.0"
verinfo = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(1, 0, 0, 0), prodvers=(1, 0, 0, 0),
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
