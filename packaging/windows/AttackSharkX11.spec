# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).parents[1]
SRC = ROOT / "src"

block_cipher = None

a = Analysis(
    [str(ROOT / "asx11_battery.py")],
    pathex=[str(SRC), str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "assets" / "attack_shark_x11.ico"), "assets"),
        (str(ROOT / "assets" / "attack_shark_x11.png"), "assets"),
    ],
    hiddenimports=[
        "hid",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pystray"],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AttackSharkX11",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "attack_shark_x11.ico"),
    version=str(ROOT / "packaging" / "windows" / "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AttackSharkX11",
)
