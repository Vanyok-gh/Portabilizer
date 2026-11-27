@echo off
chcp 65001 >nul
rem Запасной запуск Portabilizer. Сначала пробует Portabilizer.exe. Если компьютер его блокирует
rem (например, "Access is denied" на учебных и рабочих компьютерах), открывает программу через Python
rem из исходников: нужен Python с Tkinter и папка с portabilizer_v8.py (рядом, в source, в ..\source или на уровень выше).
set "PZ_ARGS=--r"
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
call :findpy
if defined PZ_PYW ( start "" "%PZ_PYW%" "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %* & exit /b 0 )
where python >nul 2>&1 || goto nopy
python "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %*
if errorlevel 1 pause
exit /b
:nopy
echo Python не найден.
set "PZ_INST="
for %%I in ("%~dp0python-*-amd64.exe" "%~dp0python_installer\python-*-amd64.exe" "%~dp0..\python_installer\python-*-amd64.exe") do if exist "%%~I" set "PZ_INST=%%~I"
if not defined PZ_INST goto noinst
echo Найден установщик Python: %PZ_INST%
echo Он поставит Python только для вашего пользователя: права администратора не нужны, система не меняется.
choice /c YN /m "Установить Python сейчас (Y - да, N - нет)"
if errorlevel 2 goto noinst
"%PZ_INST%" /passive InstallAllUsers=0 PrependPath=1 Include_test=0 Include_launcher=0 Shortcuts=0
if errorlevel 1 goto instfail
call :findpy
if not defined PZ_PYW goto instfail
start "" "%PZ_PYW%" "%PZ_DIR%\portabilizer_v8.py" %PZ_ARGS% %*
exit /b 0
:instfail
echo.
echo Установщик Python не завершился успешно. Возможно, на этом компьютере установка программ запрещена политикой.
echo Обходить это не нужно: попросите администратора поставить Python 3 с Tkinter или запустите Portabilizer.exe на другом компьютере.
pause
exit /b 1
:noinst
echo Установите Python 3 с Tkinter для текущего пользователя: https://www.python.org/downloads/windows/
echo ^(в установщике оставьте Tcl/Tk, не выбирайте "Install for all users"^).
echo Либо положите рядом с этим файлом установщик python-3.xx.x-amd64.exe: тогда этот файл предложит поставить его сам.
pause
exit /b 1
:nosrc
echo Рядом нет исходников Portabilizer (portabilizer_v8.py), запустить через Python нельзя.
echo Скачайте папку с исходниками целиком (GitHub: Code - Download ZIP) и положите этот файл рядом с portabilizer_v8.py.
pause
exit /b 1

:findpy
rem Python, поставленный для текущего пользователя (администратор не нужен): обычный установщик или менеджер Python.
set "PZ_PYW="
for /d %%P in ("%LocalAppData%\Programs\Python\Python3*" "%LocalAppData%\Python\pythoncore-*") do if exist "%%~P\pythonw.exe" set "PZ_PYW=%%~P\pythonw.exe"
exit /b 0
