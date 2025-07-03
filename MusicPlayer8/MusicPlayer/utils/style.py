"""Style utilities for the music player application"""
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

def apply_style(app):
    """Apply custom styling to the application"""
    # Set dark theme palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    # Set stylesheet for additional styling
    style = """
        QToolTip {
            color: #ffffff;
            background-color: #2a82da;
            border: 1px solid white;
        }
        
        QListWidget {
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 4px;
            padding: 5px;
        }
        
        QPushButton {
            padding: 5px;
            border-radius: 3px;
        }
        
        QPushButton:hover {
            background: #3a3a3a;
        }
    """
    
    # 过滤掉不支持的CSS属性
    filtered_style = "\n".join(
        line for line in style.splitlines()
        if not any(prop in line for prop in [
            "transition", "transform", "box-shadow"
        ])
    )
    app.setStyleSheet(filtered_style)