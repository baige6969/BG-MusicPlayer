@echo off
chcp 936 > nul
SETLOCAL EnableDelayedExpansion

:: 统一打包脚本 - 使用本地VLC安装包

:: 设置路径
set VLC_INSTALLER=C:\Users\28926\Downloads\vlc-3.0.21-win64.exe
set VLC_PATH=C:\Program Files\VideoLAN\VLC

:: 检查必要工具
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo 错误: 未找到Python环境
    pause
    exit /b 1
)

:: 安装VLC播放器
if not exist "%VLC_PATH%\vlc.exe" (
    if exist "%VLC_INSTALLER%" (
        echo 正在安装VLC播放器...
        start /wait "" "%VLC_INSTALLER%" /S
        timeout /t 30 > nul
        
        if not exist "%VLC_PATH%\vlc.exe" (
            echo 错误: VLC安装失败
            pause
            exit /b 1
        )
    else (
        echo 错误: 未找到VLC安装包
        echo 请确认文件存在: %VLC_INSTALLER%
        pause
        exit /b 1
    )
)

:: 创建打包目录结构
if not exist "dist" mkdir dist
if not exist "build" mkdir build

:: 复制VLC运行时
echo 正在复制VLC运行时...
xcopy /E /I /Q "%VLC_PATH%" "dist\vlc"

:: 安装Python依赖
echo 正在安装Python依赖...
pip install -r requirements.txt

:: 执行打包
echo 正在打包应用程序...
pyinstaller --onefile --windowed ^
    --icon=assets/icon.ico ^
    --add-data "%VLC_PATH%\*;vlc" ^
    --hidden-import=vlc ^
    --hidden-import=PyQt5.sip ^
    --noconfirm ^
    --clean ^
    main.py

if exist "dist\main.exe" (
    echo.
    echo ========================
    echo 打包成功完成!
    echo 可执行文件位于: %cd%\dist\main.exe
    echo 包含: Python、VLC和所有依赖
    echo ========================
    echo 最终程序大小: 
    dir /-C "dist\main.exe" | find "main.exe"
) else (
    echo.
    echo ========================
    echo 打包失败!
    echo ========================
)

pause