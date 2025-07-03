@echo off
chcp 65001 > nul
REM MusicPlayer build script (using spec file)

echo Building MusicPlayer...
echo.

set PYTHON_CMD=python
set "PROJECT_DIR=%~dp0"
set "VLC_PATH=D:\VLC"

REM Verify VLC installation
if not exist "%VLC_PATH%" (
    echo ERROR: VLC not found at: %VLC_PATH%
    echo Please install VLC to this path or modify VLC_PATH in build.bat
    exit /b 1
)

echo Detected VLC path: %VLC_PATH%
set "VLC_PLUGIN_PATH=%VLC_PATH%\plugins"
set "PATH=%VLC_PATH%;%PATH%"

REM Verify Python and PyInstaller
echo Checking Python environment...
"%PYTHON_CMD%" -c "import sys; assert sys.version_info >= (3, 8), 'Python 3.8+ required'"
if %errorlevel% neq 0 exit /b %errorlevel%

"%PYTHON_CMD%" -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    "%PYTHON_CMD%" -m pip install --user pyinstaller
    if %errorlevel% neq 0 exit /b %errorlevel%
)

REM Clean previous builds
echo Cleaning build directories...
rd /s /q "build" 2>nul
rd /s /q "dist" 2>nul

REM Install dependencies
echo Installing dependencies...
"%PYTHON_CMD%" -m pip install --user --upgrade pip
"%PYTHON_CMD%" -m pip install --user -r "requirements.txt"
if %errorlevel% neq 0 (
    echo ERROR: Failed to install dependencies
    exit /b %errorlevel%
)

REM Verify resource files
echo Verifying resource files...
if not exist "MusicPlayer\resources\" (
    echo ERROR: Missing resource directory: MusicPlayer\resources
    exit /b 1
)

REM Build using spec file
echo Starting build process...
"%PYTHON_CMD%" -m PyInstaller MusicPlayer.spec --noconfirm

REM Copy resource files
if %errorlevel% equ 0 (
    echo Copying resource files...
    if not exist "dist\MusicPlayer\" mkdir "dist\MusicPlayer"
    xcopy /Y "metadata_cache.db" "dist\MusicPlayer\" > nul
    xcopy /E /I /Y "cover_cache" "dist\MusicPlayer\cover_cache\" > nul
    
    REM Copy VLC plugins if available
    if exist "%VLC_PLUGIN_PATH%" (
        xcopy /E /I /Y "%VLC_PLUGIN_PATH%" "dist\MusicPlayer\plugins\" > nul
    )
)

if %errorlevel% equ 0 (
    echo.
    echo BUILD SUCCESSFUL!
    echo Executable: %PROJECT_DIR%dist\MusicPlayer.exe
    
    if defined VLC_PATH (
        echo NOTE: Requires VLC environment - %VLC_PATH%
    ) else (
        echo WARNING: VLC path not configured, please install VLC and set VLC_DIR
    )
) else (
    echo.
    echo BUILD FAILED!
    echo Possible reasons:
    echo 1. Missing dependencies (pip install -r requirements.txt)
    echo 2. PyInstaller issues (pip install --upgrade pyinstaller)
    echo 3. Incorrect VLC path (set VLC_DIR environment variable)
    echo 4. Resource files missing (check MusicPlayer\resources directory)
)

pause