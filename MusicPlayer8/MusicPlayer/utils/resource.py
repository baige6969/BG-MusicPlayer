import os
import sys
from pathlib import Path

def resource_path(relative_path):
    """获取打包后资源的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # 打包后的资源路径
        base_path = Path(sys._MEIPASS)
    else:
        # 开发时的资源路径
        base_path = Path(__file__).parent.parent
    
    return str(base_path / 'resources' / relative_path)

def get_style_path():
    """获取样式表路径"""
    return resource_path('style.qss')

def get_icon_path():
    """获取图标路径"""
    return resource_path('icon.ico')

def load_icon(icon_name):
    """加载图标文件"""
    try:
        icon_path = resource_path(icon_name)
        if os.path.exists(icon_path):
            return icon_path
        return None
    except Exception as e:
        print(f"加载图标失败: {e}")
        return None

def load_style():
    """加载样式表"""
    try:
        style_path = get_style_path()
        if os.path.exists(style_path):
            with open(style_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    except Exception as e:
        print(f"加载样式表失败: {e}")
        return ""