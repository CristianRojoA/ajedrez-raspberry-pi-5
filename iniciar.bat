@echo off
REM ============================================================================
REM  Lanzador de la app de ajedrez (Kivy).
REM  Usa automaticamente un Python que TENGA Kivy instalado.
REM  El .venv del proyecto es Python 3.14 y aun NO tiene wheels de Kivy,
REM  por eso aqui se prefiere el venv de pruebas 3.12 o el Python 3.12 global.
REM ============================================================================
setlocal
cd /d "%~dp0"

REM 1) venv de pruebas 3.12 (si existe)
set "PY=%~dp0.venv-test\Scripts\python.exe"
if exist "%PY%" goto run

REM 2) Python 3.12 global del usuario
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if exist "%PY%" goto run

REM 3) py launcher pidiendo 3.12 explicitamente
where py >nul 2>nul && (set "PY=py -3.12" & goto run)

echo No se encontro un Python 3.12 con Kivy instalado.
echo Instala Kivy con:  py -3.12 -m pip install kivy
pause
exit /b 1

:run
echo Iniciando ajedrez con: %PY%
"%PY%" "%~dp0vistafrancisco.py"
if errorlevel 1 (
    echo.
    echo La app termino con error. Revisa el mensaje de arriba.
    pause
)
endlocal
