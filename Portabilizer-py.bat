@echo off
rem Запуск Portabilizer из исходников, без Portabilizer.exe (для компьютеров, где exe блокируется).
rem Нужен установленный Python с Tkinter. Параметры передаются дальше, например: Portabilizer-py.bat --r
rem Исходники ищутся рядом с этим файлом или в подпапке source.
set "PZ_DIR=%~dp0"
if not exist "%PZ_DIR%portabilizer_v8.py" set "PZ_DIR=%~dp0source\"
if not exist "%PZ_DIR%portabilizer_v8.py" (
  echo Не найден portabilizer_v8.py: положите этот файл рядом с исходниками или в папку с подпапкой source.
  pause
  exit /b 1
)
cd /d "%PZ_DIR%"
rem Сначала без консольного окна (pythonw), затем через py-лаунчер, затем обычный python.
where pythonw >nul 2>&1 && ( start "" pythonw "%PZ_DIR%portabilizer_v8.py" %* & exit /b 0 )
where pyw >nul 2>&1 && ( start "" pyw "%PZ_DIR%portabilizer_v8.py" %* & exit /b 0 )
where python >nul 2>&1 && ( python "%PZ_DIR%portabilizer_v8.py" %* & goto end )
echo Python не найден в PATH.
:end
if errorlevel 1 pause
