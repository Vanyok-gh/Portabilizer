@echo off
chcp 65001 >nul
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
call :findpy
if defined PZ_PYW ( start "" "%PZ_PYW%" "%PZ_DIR%portabilizer_v8.py" %* & exit /b 0 )
where python >nul 2>&1 && ( python "%PZ_DIR%portabilizer_v8.py" %* & goto end )
goto nopy
:end
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
start "" "%PZ_PYW%" "%PZ_DIR%portabilizer_v8.py" %*
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

:findpy
rem Python, поставленный для текущего пользователя (администратор не нужен): обычный установщик или менеджер Python.
set "PZ_PYW="
for /d %%P in ("%LocalAppData%\Programs\Python\Python3*" "%LocalAppData%\Python\pythoncore-*") do if exist "%%~P\pythonw.exe" set "PZ_PYW=%%~P\pythonw.exe"
exit /b 0
