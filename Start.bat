@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "VENV=%~dp0.venv"
set "PY=%VENV%\Scripts\pythonw.exe"
REM Verschobenes Projekt: die .venv hat den alten Pfad in ihren Startern. Der Ordner
REM wird in .venv\.folder gemerkt. Der Merker wird erst nach fertiger Einrichtung
REM geschrieben: fehlt er, wurde die Einrichtung abgebrochen und laeuft neu.
set "MARK=%VENV%\.folder"
set "OLDDIR="
if exist "%VENV%\Scripts\python.exe" if exist "%MARK%" set /p OLDDIR=<"%MARK%"
if exist "%VENV%\Scripts\python.exe" if /i not "%OLDDIR%"=="%~dp0" (
    echo [AktionskartenGenerator] .venv ist unvollstaendig oder gehoert zu einem anderen Ordner - wird neu angelegt ...
    rmdir /s /q "%VENV%"
)
if not exist "%VENV%\Scripts\python.exe" (
    echo [AktionskartenGenerator] Erste Einrichtung: virtuelle Umgebung wird angelegt ...
    py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
    if errorlevel 1 ( echo Python 3 nicht gefunden. Bitte Python 3.10 oder neuer installieren. & pause & exit /b 1 )
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
    "%VENV%\Scripts\python.exe" -m pip install -r "%~dp0App\requirements.txt"
    if errorlevel 1 ( echo Installation der Pakete fehlgeschlagen. & pause & exit /b 1 )
    >"%MARK%" echo(%~dp0
)
start "" "%PY%" "%~dp0App\AktionskartenGenerator.py"
endlocal
