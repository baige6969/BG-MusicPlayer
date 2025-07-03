"""
MusicPlayer - 完整的音乐播放解决方案

主要功能:
- 本地音乐播放管理
- 云音乐服务集成
- 用户界面管理
- 资源统一管理

包级功能:
- get_resource(path): 获取资源文件路径
- VERSION: 当前版本号
"""

import os
from typing import Union

from .version import __version__
from MusicPlayer.ui.main_window import MainWindow
from MusicPlayer.ui.login_dialog import LoginDialog
from MusicPlayer.player import MusicPlayer
from MusicPlayer.cloudmusic_service import CloudMusicService as CloudService

# 资源目录路径
_RESOURCE_DIR = os.path.join(os.path.dirname(__file__), "resources")

def get_resource(relative_path: str) -> str:
    """
    获取资源文件绝对路径
    
    参数:
        relative_path: 相对于resources目录的路径
        
    返回:
        资源文件的绝对路径
    """
    return os.path.join(_RESOURCE_DIR, relative_path)

VERSION = __version__

__all__ = [
    '__version__',
    'MusicPlayer',
    'MainWindow',
    'LoginDialog',
    'CloudService',
    'get_resource',
    'VERSION'
]