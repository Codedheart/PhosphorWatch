@echo off
rem Run PhosphorWatch from source. Needs Python 3.10+; the first run sets up a
rem private .venv with pywebview (the only package it needs).
cd /d "%~dp0"
setlocal

set "PY="
for %%V in (3.13 3.12 3.11 3.10) do if not defined PY (py -%%V -c "1" >nul 2>&1 && set "PY=py -%%V")
if not defined PY (python -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1 && set "PY=python")
if not defined PY goto :nopy

if exist .venv\Scripts\python.exe (
  .venv\Scripts\python -c "import sys; sys.exit(sys.version_info < (3,10))" >nul 2>&1 || rmdir /s /q .venv
)
if not exist .venv\Scripts\python.exe (
  echo Setting up PhosphorWatch with %PY% ...
  %PY% -m venv .venv || goto :err
)
.venv\Scripts\python -c "import webview" >nul 2>&1 || (
  echo Installing pywebview...
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\python -m pip install -q -r requirements.txt || goto :err
)

if not exist phosphor\assets\VT323-Regular.ttf call :font
rem pythonw runs it without a console window; pass --debug for WebView devtools
start "" .venv\Scripts\pythonw.exe phosphor_watch.py %*
exit /b 0

:font
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing 'https://github.com/google/fonts/raw/main/ofl/vt323/VT323-Regular.ttf' -OutFile 'phosphor\assets\VT323-Regular.ttf'; Invoke-WebRequest -UseBasicParsing 'https://github.com/google/fonts/raw/main/ofl/vt323/OFL.txt' -OutFile 'phosphor\assets\VT323-OFL.txt' } catch { Write-Host 'VT323 font download skipped (falls back to Lucida Console)' }"
exit /b 0

:nopy
echo.
echo PhosphorWatch needs Python 3.10 or newer, and none was found.
echo Install the latest Python from https://www.python.org/downloads/
echo  - tick "Add python.exe to PATH" and keep "py launcher" checked
echo then double-click run.bat again.
echo.
echo (Or skip Python entirely: download PhosphorWatch-windows.zip from the Releases page.)
pause
exit /b 1

:err
echo.
echo Setup failed - see the messages above.
pause
exit /b 1
