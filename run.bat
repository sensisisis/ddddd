@echo off
setlocal
cd /d "%~dp0"

echo [1/3] Python...
where python >nul 2>&1
if errorlevel 1 (
    echo    Python no encontrado. Instala Python 3.10+.
    pause & exit /b 1
)
python --version

echo [2/3] Dependencias...
python -m pip install -q -r requirements.txt

echo [3/3] Backend...
python aimbot_server.py
pause