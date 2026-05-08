# -*- mode: python ; coding: utf-8 -*-

import os
import re
import glob

_spec_dir = os.path.dirname(os.path.abspath(SPEC))
icon_dir = os.path.join(_spec_dir, "BS_corr_plotter", "media")
icon_files = sorted(glob.glob(os.path.join(icon_dir, "*.ico")))
icon_arg = icon_files[0] if icon_files else None
app_py_path = os.path.join(_spec_dir, "BS_corr_plotter.py")

version = "0.0"
try:
    with open(app_py_path, "r", encoding="utf-8") as f:
        app_source = f.read()
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', app_source, re.MULTILINE)
    if m:
        version = m.group(1)
except OSError:
    pass

exe_name = f"BS_corr_plotter_v{version}"


a = Analysis(
    ['BS_corr_plotter.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=exe_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_arg,
)
