@echo off
chcp 65001 >nul
cd /d "%~dp0\.."
echo === Сборка встроенных наборов библиотек (Visual C++, OpenAL) в папку dx ===
python --version >nul 2>&1
if errorlevel 1 (
  echo Python не найден. Установите Python 3.9 или новее с python.org, отметив Add Python to PATH.
  pause
  exit /b 1
)
python tools\collect_redist.py %*
echo.
pause
