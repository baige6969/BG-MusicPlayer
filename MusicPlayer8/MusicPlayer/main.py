import sys
import os
import traceback
import logging
from logging.handlers import RotatingFileHandler

# 配置日志
def setup_logging():
    """配置应用程序日志"""
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # 文件日志 (最大10MB，保留3个备份)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "music_player.log"),
        maxBytes=10*1024*1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(file_handler)
    
    # 控制台日志
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s - %(message)s'
    ))
    logger.addHandler(console_handler)

# 确保项目根目录在Python路径中
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from MusicPlayer.ui.main_window import MainWindow

def handle_exception(exc_type, exc_value, exc_traceback):
    """全局异常处理函数"""
    # 跳过PyQt内部异常
    if exc_type.__name__ == "TypeError" and "sipBadCatcherResult" in str(exc_value):
        logging.error("PyQt信号处理异常: %s", str(exc_value))
        return
    
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logging.error("未处理的异常: %s", error_msg)
    
    try:
        # 显示简化错误对话框
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("程序发生错误")
        msg.setInformativeText(str(exc_value))
        msg.setWindowTitle("错误")
        
        # 在主线程安全显示对话框
        if QApplication.instance():
            msg.exec_()
        else:
            print(f"无法显示错误对话框: {error_msg}")
    except Exception as e:
        logging.error("处理异常时出错: %s", str(e))

# 资源路径缓存
_resource_cache = {}

def get_resource_path(*path_parts):
    """统一获取资源路径"""
    cache_key = ":".join(path_parts)
    if cache_key in _resource_cache:
        return _resource_cache[cache_key]
    
    # 规范化路径部分
    norm_parts = [p.replace("\\", "/").strip("/") for p in path_parts]
    
    # 优先检查打包环境资源路径
    if getattr(sys, 'frozen', False):
        try:
            base_path = sys._MEIPASS
            path = os.path.join(base_path, *norm_parts)
            if os.path.exists(path):
                _resource_cache[cache_key] = path
                logging.debug(f"[打包环境] 找到资源: {'/'.join(norm_parts)} -> {path}")
                return path
        except Exception as e:
            logging.debug(f"[打包环境] 资源查找异常: {str(e)}")
    
    # 开发环境资源路径
    search_paths = [
        # 1. 项目resources目录
        os.path.join(os.path.dirname(__file__), "..", "resources", *norm_parts),
        
        # 2. 项目根目录resources
        os.path.join(os.path.dirname(__file__), "..", "..", "resources", *norm_parts),
        
        # 3. 环境变量指定路径
        os.path.join(os.environ["RESOURCE_PATH"], *norm_parts) 
            if "RESOURCE_PATH" in os.environ else None,
    ]
    
    for path in search_paths:
        try:
            if path and os.path.exists(path):
                _resource_cache[cache_key] = path
                logging.debug(f"[开发环境] 找到资源: {'/'.join(norm_parts)} -> {path}")
                return path
        except Exception as e:
            logging.debug(f"[开发环境] 资源查找异常: {str(e)}")
            continue
    
    logging.warning(f"未找到资源: {'/'.join(norm_parts)}")
    return None

def load_stylesheet(app):
    """加载应用程序样式表"""
    stylesheet_path = get_resource_path("resources", "styles.qss")
    if stylesheet_path:
        try:
            with open(stylesheet_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
            print(f"成功加载样式表: {stylesheet_path}")
        except Exception as e:
            print(f"加载样式表出错: {str(e)}")
    else:
        print("警告: 未找到样式表文件")

def check_resources():
    """检查必要的资源文件"""
    required_files = {
        "样式表": "styles.qss",
        "应用图标": os.path.join("icons", "app.ico")
    }
    
    missing = []
    backup_found = False
    
    # 检查主要资源路径
    for name, rel_path in required_files.items():
        path = get_resource_path("resources", rel_path)
        if not path or not os.path.exists(path):
            missing.append(f"{name}: {rel_path}")
            logging.error(f"资源文件缺失: {rel_path}")
    
    # 如果主要资源缺失，尝试备份资源
    if missing:
        backup_dir = os.path.join(os.path.dirname(__file__), "..", "resources_backup")
        if os.path.exists(backup_dir):
            logging.info(f"尝试使用备份资源目录: {backup_dir}")
            os.environ["RESOURCE_PATH"] = backup_dir
            backup_found = True
            
            # 重新检查资源
            missing = []
            for name, rel_path in required_files.items():
                path = get_resource_path("resources", rel_path)
                if not path:
                    missing.append(f"{name}: {rel_path}")
    
    if missing:
        error_msg = "缺少必要的资源文件:\n" + "\n".join(missing)
        if backup_found:
            error_msg += "\n\n警告: 使用了备份资源，某些功能可能受限"
        else:
            error_msg += "\n\n建议: 请重新安装应用程序或联系技术支持"
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("资源文件错误")
        msg.setInformativeText(error_msg)
        msg.setWindowTitle("错误")
        msg.exec_()
        
        return backup_found  # 如果有备份资源，仍允许继续运行
    
    # 设置找到的资源路径到环境变量
    if required_files["样式表"]:
        resource_dir = os.path.dirname(os.path.dirname(required_files["样式表"]))
        os.environ["RESOURCE_PATH"] = resource_dir
        print(f"设置资源路径: {resource_dir}")
    
    return True

def main():
    """应用程序入口"""
    print("启动日志: 初始化应用程序...")
    
    # 必须先初始化QApplication
    app = QApplication(sys.argv)
    
    # 设置全局异常处理
    sys.excepthook = handle_exception
    
    # 打印详细路径信息
    print(f"当前工作目录: {os.getcwd()}")
    print(f"模块目录: {os.path.dirname(__file__)}")
    print(f"Python路径: {sys.path}")
    
    # 检查资源文件
    if not check_resources():
        print("错误: 缺少必要的资源文件")
        # 尝试使用备用资源路径
        alt_resource_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
        print(f"尝试备用资源路径: {alt_resource_dir}")
        if os.path.exists(alt_resource_dir):
            print("找到备用资源路径")
            os.environ["RESOURCE_PATH"] = alt_resource_dir
        else:
            sys.exit(1)
    
    try:
        print("启动日志: 加载样式表...")
        load_stylesheet(app)
        
        print("启动日志: 创建主窗口...")
        player = MainWindow()
        print(f"主窗口创建成功: {player}")
        
        # 设置窗口图标
        icon_path = get_resource_path("resources", "icons", "app.ico")
        print(f"图标路径: {icon_path}")
        
        if icon_path:
            try:
                print("启动日志: 设置窗口图标...")
                player.setWindowIcon(QIcon(icon_path))
                print("窗口图标设置成功")
            except Exception as e:
                print(f"设置窗口图标出错: {str(e)}")
        else:
            print("警告: 未找到图标文件")
        
        print("启动日志: 显示主窗口...")
        player.show()
        print(f"窗口显示状态: {player.isVisible()}")
        print(f"窗口尺寸: {player.size()}")
        print(f"窗口标题: {player.windowTitle()}")
        
        print("启动日志: 进入主事件循环...")
        ret = app.exec_()
        print(f"启动日志: 应用程序退出，返回码: {ret}")
        sys.exit(ret)
    except Exception as e:
        handle_exception(type(e), e, e.__traceback__)
        sys.exit(1)

if __name__ == "__main__":
    main()