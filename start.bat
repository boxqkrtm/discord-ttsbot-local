@echo off
setlocal

cd /d "%~dp0"

call :setup_ffmpeg
if errorlevel 1 goto error

call :setup_env
if errorlevel 1 goto error

call :load_env

call :setup_uv_python
if errorlevel 1 goto error

call :setup_venv
if errorlevel 1 goto error

echo.
echo Starting VoxCPM Discord bot...
".venv\Scripts\python.exe" -c "from voxcpm_discord.app import main; main()"

set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo Bot exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%

:setup_ffmpeg
if defined VOXCPM_FFMPEG_BIN set "PATH=%VOXCPM_FFMPEG_BIN%;%PATH%"
call :detect_ffmpeg
if not errorlevel 1 exit /b 0

echo ffmpeg not found. Installing with winget...
where winget >nul 2>nul
if errorlevel 1 (
    echo winget not found. Install ffmpeg manually and try again.
    exit /b 1
)

winget install -e --id Gyan.FFmpeg
if errorlevel 1 exit /b 1

call :detect_ffmpeg
if errorlevel 1 (
    echo ffmpeg was installed, but the path was not found. Reopen this window and run start.bat again.
    exit /b 1
)
exit /b 0

:detect_ffmpeg
where ffmpeg >nul 2>nul
if not errorlevel 1 exit /b 0

for /d %%D in ("%LocalAppData%\Microsoft\WinGet\Packages\Gyan.FFmpeg_*") do (
    for /d %%B in ("%%~fD\ffmpeg-*\bin") do (
        if exist "%%~fB\ffmpeg.exe" (
            set "FFMPEG_BIN=%%~fB"
            set "PATH=%%~fB;%PATH%"
            setx VOXCPM_FFMPEG_BIN "%%~fB" >nul
            exit /b 0
        )
    )
)
exit /b 1

:setup_env
if exist ".env" exit /b 0

echo.
echo First setup
echo 1. CPU
echo 2. NVIDIA CUDA
choice /c 12 /n /m "Select runtime [1-2]: "
if errorlevel 2 (
    set "VOXCPM_DEVICE_VALUE=cuda"
    set "VOXCPM_DTYPE_VALUE=float16"
) else (
    set "VOXCPM_DEVICE_VALUE=cpu"
    set "VOXCPM_DTYPE_VALUE=float32"
)

echo.
set /p "DISCORD_TOKEN_VALUE=Discord bot token: "
if "%DISCORD_TOKEN_VALUE%"=="" (
    echo DISCORD_TOKEN is required.
    exit /b 1
)

> ".env" (
    echo DISCORD_TOKEN=%DISCORD_TOKEN_VALUE%
    echo VOXCPM_MODEL=openbmb/VoxCPM2
    echo VOXCPM_MODEL_DATA_DIR=data
    echo VOXCPM_DEVICE=%VOXCPM_DEVICE_VALUE%
    echo VOXCPM_DTYPE=%VOXCPM_DTYPE_VALUE%
    echo VOXCPM_DATA_DIR=data-user
    echo LOG_LEVEL=INFO
)
exit /b 0

:load_env
if exist ".env" (
    for /f "usebackq eol=# tokens=1,* delims==" %%A in (".env") do set "%%A=%%B"
)
exit /b 0

:setup_uv_python
call :setup_uv
if errorlevel 1 exit /b 1

echo Ensuring Python 3.11 is available via uv...
"%UV%" python install 3.11
if errorlevel 1 exit /b 1

exit /b 0

:setup_uv
set "UV="
for %%I in (uv.exe) do set "UV=%%~$PATH:I"
if defined UV exit /b 0

if exist "%LocalAppData%\Microsoft\WinGet\Links\uv.exe" (
    set "UV=%LocalAppData%\Microsoft\WinGet\Links\uv.exe"
    exit /b 0
)

for /d %%D in ("%LocalAppData%\Microsoft\WinGet\Packages\Astral-sh.uv_*") do (
    if exist "%%~fD\uv.exe" (
        set "UV=%%~fD\uv.exe"
        exit /b 0
    )
    if exist "%%~fD\uv\uv.exe" (
        set "UV=%%~fD\uv\uv.exe"
        exit /b 0
    )
)

echo uv not found. Installing with winget...
where winget >nul 2>nul
if errorlevel 1 (
    echo winget not found. Install uv manually and try again.
    exit /b 1
)

winget install -e --id Astral-sh.uv
if errorlevel 1 exit /b 1

for %%I in (uv.exe) do set "UV=%%~$PATH:I"
if defined UV exit /b 0

if exist "%LocalAppData%\Microsoft\WinGet\Links\uv.exe" (
    set "UV=%LocalAppData%\Microsoft\WinGet\Links\uv.exe"
    exit /b 0
)

for /d %%D in ("%LocalAppData%\Microsoft\WinGet\Packages\Astral-sh.uv_*") do (
    if exist "%%~fD\uv.exe" (
        set "UV=%%~fD\uv.exe"
        exit /b 0
    )
    if exist "%%~fD\uv\uv.exe" (
        set "UV=%%~fD\uv\uv.exe"
        exit /b 0
    )
)

echo uv was installed, but the executable path was not found. Run start.bat again or install uv manually.
exit /b 1

:setup_venv
if exist ".venv\Scripts\python.exe" exit /b 0
if exist ".venv" (
    echo Removing incomplete .venv...
    rmdir /s /q ".venv"
)

echo.
echo Creating .venv with uv...
"%UV%" venv .venv --python 3.11
if errorlevel 1 exit /b 1
if not exist ".venv\Scripts\python.exe" (
    echo Failed to create .venv correctly.
    exit /b 1
)

echo Installing dependencies with uv...
"%UV%" pip install --python ".venv\Scripts\python.exe" --upgrade pip
if errorlevel 1 exit /b 1

if /i "%VOXCPM_DEVICE%"=="cuda" (
    "%UV%" pip install --python ".venv\Scripts\python.exe" torch torchaudio --index-url https://download.pytorch.org/whl/cu128
) else (
    "%UV%" pip install --python ".venv\Scripts\python.exe" torch torchaudio
)
if errorlevel 1 exit /b 1

"%UV%" pip install --python ".venv\Scripts\python.exe" -e .
if errorlevel 1 exit /b 1

exit /b 0

:error
echo.
echo Setup failed.
pause
exit /b 1
