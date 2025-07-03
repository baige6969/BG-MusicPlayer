@echo off
chcp 936 > nul
SETLOCAL

:: 压缩包创建脚本

:: 设置路径
set MAIN_EXE=dist\main.exe
set VLC_INSTALLER=C:\Users\28926\Downloads\vlc-3.0.21-win64.exe
set OUTPUT_DIR=dist\release_packages

:: 检查main.exe
if not exist "%MAIN_EXE%" (
    echo 错误: 未找到main.exe
    echo 请先运行complete_package.bat进行打包
    pause
    exit /b 1
)

:: 检查VLC安装包
if not exist "%VLC_INSTALLER%" (
    echo 警告: 未找到VLC安装包
    echo 请确认文件存在: %VLC_INSTALLER%
    pause
)

:: 创建输出目录
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

:: 创建仅含main.exe的压缩包
echo 正在创建MusicPlayer_Standalone.zip...
powershell -Command "Compress-Archive -Path '%MAIN_EXE%' -DestinationPath '%OUTPUT_DIR%\MusicPlayer_Standalone.zip' -Force"

:: 创建包含VLC的压缩包
if exist "%VLC_INSTALLER%" (
    echo 正在创建MusicPlayer_With_VLC.zip...
    powershell -Command "$files = @('%MAIN_EXE%', '%VLC_INSTALLER%'); Compress-Archive -Path $files -DestinationPath '%OUTPUT_DIR%\MusicPlayer_With_VLC.zip' -Force"
)

:: 结果报告
echo.
echo ========================
echo 压缩包创建完成!
echo 输出目录: %cd%\%OUTPUT_DIR%
echo.
echo 包含文件:
dir /B "%OUTPUT_DIR%"
echo ========================
echo 文件大小:
dir /-C "%OUTPUT_DIR%\*.zip"
echo ========================

pause