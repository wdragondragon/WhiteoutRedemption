# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['WhiteoutRedemption_ui.py'],
    pathex=[],
    binaries=[],
    datas=[('images/icon.png','images/'),('ddddocr/ddddocr/','ddddocr/')],
    hiddenimports=['onnxruntime'],
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
    name='无尽冬日-礼包兑换工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='./images/icon.png'
)
