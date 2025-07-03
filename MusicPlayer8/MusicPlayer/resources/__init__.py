"""Resources package"""
import os
from PyQt5.QtGui import QIcon

def get_icon_path(icon_name):
    """Get absolute path to icon resource"""
    return os.path.join(os.path.dirname(__file__), 'icons', icon_name)

def get_style_path():
    """Get absolute path to stylesheet"""
    return os.path.join(os.path.dirname(__file__), 'styles.qss')

__all__ = ['get_icon_path', 'get_style_path']