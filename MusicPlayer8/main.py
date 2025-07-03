#!/usr/bin/env python3
import sys
import logging
from PyQt5.QtWidgets import QApplication
from MusicPlayer.ui import main_window

def configure_logging():
    """配置应用程序日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)-8s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler()]
    )
    # 减少Qt框架的调试日志
    logging.getLogger('PyQt5').setLevel(logging.WARNING)

def main():
    """应用程序主入口"""
    configure_logging()
    
    try:
        app = QApplication(sys.argv)
        window = main_window.MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logging.critical(f"应用程序启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()