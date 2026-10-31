@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Сборка Portabilizer
echo === Сборка Portabilizer.exe: одно приложение, окно и командная строка ===
echo.
python --version >nul 2>&1
if errorlevel 1 (
  echo Python не найден. Установите Python 3.9 или новее с python.org, отметив Add Python to PATH.
  pause
  exit /b 1
)
if not exist "portabilizer_v8.py" (
  echo Не найден portabilizer_v8.py: положите его рядом с build.bat.
  pause
  exit /b 1
)
if not exist "assets\portabilizer.ico" (
  echo Не найдена папка assets с иконкой portabilizer.ico рядом с build.bat.
  pause
  exit /b 1
)
echo [1/3] Ставлю pyinstaller и psutil...
python -m pip install --upgrade pyinstaller psutil
if errorlevel 1 goto fail
set "ADD="
if exist "7z.exe" (set ADD=%ADD% --add-binary "7z.exe;.") else if exist "tools\7z.exe" set ADD=%ADD% --add-binary "tools\7z.exe;."
if exist "7z.dll" (set ADD=%ADD% --add-binary "7z.dll;.") else if exist "tools\7z.dll" set ADD=%ADD% --add-binary "tools\7z.dll;."
if exist "innoextract.exe" (set ADD=%ADD% --add-binary "innoextract.exe;.") else if exist "tools\innoextract.exe" set ADD=%ADD% --add-binary "tools\innoextract.exe;."
if exist "dx\*.cab" set ADD=%ADD% --add-data "dx;dx"
if not exist "7z.exe" if not exist "tools\7z.exe" echo ВНИМАНИЕ: 7z.exe не найден. Без него Portabilizer не распакует архивы. Положите 7z.exe и 7z.dll рядом с build.bat и соберите заново.
echo [2/3] Собираю exe, это займёт минуту-две...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name Portabilizer --icon "assets\portabilizer.ico" %ADD% portabilizer_v8.py
if errorlevel 1 goto fail
echo [3/3] Готовлю ярлык Portabilizer (R)...
copy /Y "assets\portabilizer_R.ico" "dist\portabilizer_R.ico" >nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=(Resolve-Path 'dist').Path; $s=(New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $d 'Portabilizer (R).lnk')); $s.TargetPath=(Join-Path $d 'Portabilizer.exe'); $s.Arguments='--r'; $s.IconLocation=(Join-Path $d 'portabilizer_R.ico'); $s.WorkingDirectory=$d; $s.Save()" >nul 2>&1
echo.
echo Готово: dist\Portabilizer.exe
echo Рядом лежат ярлык Portabilizer (R).lnk и portabilizer_R.ico. Иконку не удаляйте: ярлык берёт её оттуда.
pause
exit /b 0
:fail
echo.
echo Сборка не удалась. Скопируйте текст ошибки выше и пришлите мне.
pause
exit /b 1
