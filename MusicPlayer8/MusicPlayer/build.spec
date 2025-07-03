# -*- mode: python -*-
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

# 添加项目根目录到Python路径
project_root = r'C:\Users\28926\Desktop\文档\py\MusicPlayer8'
sys.path.append(project_root)

# VLC插件路径
vlc_dir = r'D:\VLC'

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        (os.path.join(project_root, 'MusicPlayer/resources'), 'resources'),
        (os.path.join(vlc_dir, '*'), 'vlc')
    ],
    hiddenimports=[
        'MusicPlayer.ui',
        'MusicPlayer.ui.main_window',
        'MusicPlayer.ui.login_dialog',
        'MusicPlayer.player',
        'MusicPlayer.cloud_service',
        'MusicPlayer.cloudmusic_service',
        'pygame'
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# 添加VLC二进制文件
for dll in os.listdir(vlc_dir):
    if dll.endswith('.dll'):
        a.binaries.append((os.path.join('vlc', dll), os.path.join(vlc_dir, dll), 'BINARY'))

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MusicPlayer'
)