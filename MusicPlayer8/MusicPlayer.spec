# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['MusicPlayer\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('MusicPlayer/resources', 'resources')],
    hiddenimports=[
        'MusicPlayer.ui.main_window', 
        'MusicPlayer.ui.login_dialog',
        'MusicPlayer.player.music_router',
        'requests'
    ],
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
    name='MusicPlayer',
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
)