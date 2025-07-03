@echo off
chcp 65001 > nul
REM MusicPlayer运行脚本

echo 正在启动MusicPlayer...
echo.

set PYTHON_CMD=python

REM 检查Python是否可用
%PYTHON_CMD% --version > nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python或未正确安装
    pause
    exit /b 1
)

REM 运行MusicPlayer主程序
%PYTHON_CMD% -c "from PyQt5.QtWidgets import QApplication; from MusicPlayer.ui import main_window; app = QApplication([]); mw = main_window.MainWindow(); mw.show(); app.exec_()"

if %errorlevel% equ 0 (
    echo.
    echo MusicPlayer已正常退出
) else (
    echo.
    echo MusicPlayer启动失败!
    echo 可能原因:
    echo 1. 未安装PyQt5 (pip install PyQt5)
    echo 2. MusicPlayer模块路径问题
    echo 3. 其他依赖缺失
)

pause