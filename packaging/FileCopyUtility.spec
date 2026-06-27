# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

block_cipher = None
spec_path = Path(SPEC) if 'SPEC' in globals() else None
root = spec_path.resolve().parent.parent if spec_path else Path.cwd()

icon_path = str(root / "resources" / "icon.ico")
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "resources"), "resources"), (str(root / "logs"), "logs"), (str(root / "samples"), "samples")],
    hiddenimports=["PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="FileCopyUtility",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
)
