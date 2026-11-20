@echo off
chcp 65001 >nul
rem Запасной запуск Portabilizer. Сначала пробует Portabilizer.exe. Если компьютер его блокирует
rem (например, "Access is denied" на учебных и рабочих компьютерах), открывает программу через Python
rem из исходников: нужен Python с Tkinter и папка с portabilizer_v8.py (рядом, в source, в ..\source или на уровень выше).
set "PZ_ARGS="
if not exist "%~dp0Portabilizer.exe" goto py
start "" /wait "%~dp0Portabilizer.exe" %PZ_ARGS% %*
if not errorlevel 1 exit /b 0
echo.
echo Portabilizer.exe не запустился. Скорее всего, компьютер блокирует неподписанные exe-файлы.
:py
set "PZ_DIR="
for %%D in ("%~dp0" "%~dp0source\" "%~dp0..\source\" "%~dp0..\") do if not defined PZ_DIR if exist "%%~D\portabilizer_v8.py" set "PZ_DIR=%%~D"
if not defined PZ_DIR goto nosrc
cd /d "%PZ_DIR%"
echo Запускаю Portabilizer через Python...
where pythonw >nul 2>&1 && ( start "" pythonw "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %* & exit /b 0 )
where pyw >nul 2>&1 && ( start "" pyw "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %* & exit /b 0 )
where python >nul 2>&1 || goto nopy
python "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %*
if errorlevel 1 pause
exit /b
:nopy
echo Python не найден в PATH.
pause
exit /b 1
:nosrc
echo Рядом нет исходников Portabilizer (portabilizer_v8.py), запустить через Python нельзя.
echo Скачайте папку с исходниками целиком (GitHub: Code - Download ZIP) и положите этот файл рядом с portabilizer_v8.py.
pause
exit /b 1
