@echo off
:: Uso: tablets.bat <DISPOSITIVO> <NOMBRE> <ALIAS> <TITULO> <DISPLAY> <ANCHO> <ALTO> <X> <Y>
:: Abre la app en el usuario PRINCIPAL del dispositivo.

if "%~9"=="" (
    echo Faltan argumentos. Inicia los perfiles desde el lanzador de Python.
    exit /b 1
)

set DEV=%~1
set NOMBRE=%~2
set DEVNAME=%~3
set TITULO=%~4
set DISPLAY_SIZE=%~5
set WINDOW_WIDTH=%~6
set WINDOW_HEIGHT=%~7
set WINDOW_X=%~8
set WINDOW_Y=%~9

set APP=com.ankama.dofustouch
if "%SCRCPY_DIR%"=="" (
    echo SCRCPY_DIR no esta definido. Configuralo en .env antes de lanzar.
    exit /b 1
)
set "ScrcpyExe=%SCRCPY_DIR%\scrcpy.exe"
if not exist "%ScrcpyExe%" (
    echo No se encontro scrcpy.exe dentro de SCRCPY_DIR.
    exit /b 1
)
set "LOGDIR=%~dp0logs"
set "LOGFILE=%LOGDIR%\scrcpy_%DEVNAME%_%TITULO%.log"
set "DISPLAY_ID_PS1=%~dp0get_display_id.ps1"
if not exist "%DISPLAY_ID_PS1%" (
    echo No se encontro get_display_id.ps1 junto al lanzador.
    exit /b 1
)

if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo [%TITULO%] Verificando si la app esta en primer plano...
adb -s %DEV% shell dumpsys activity activities | findstr /C:"mResumedActivity" | findstr /C:"%APP%" >nul
if %errorlevel%==0 (
    echo App detectada en primer plano, cerrando...
    adb -s %DEV% shell am force-stop %APP%
    timeout /t 1 >nul
) else (
    echo App no esta en primer plano, no es necesario cerrarla.
)

if exist "%LOGFILE%" del "%LOGFILE%"

echo Lanzando scrcpy en segundo plano...
start /B "" "%ScrcpyExe%" -s %DEV% --new-display=%DISPLAY_SIZE% --no-vd-system-decorations --window-width=%WINDOW_WIDTH% --window-height=%WINDOW_HEIGHT% --window-title="%TITULO%" --window-x=%WINDOW_X% --window-y=%WINDOW_Y% --video-codec=h265 --video-codec-options=color-range=1 -b16M --max-fps=100 --no-audio --turn-screen-off --render-driver=opengl --start-app=%APP% -K > "%LOGFILE%" 2>&1

echo Esperando a que scrcpy reporte el display asignado...
set DISPLAY_ID=
set INTENTOS=0

:esperar_display
set /a INTENTOS+=1
if %INTENTOS% GTR 20 (
    echo No se detecto el ID de display tras varios intentos, revisa %LOGFILE%
    exit /b 1
)

for /f %%a in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%DISPLAY_ID_PS1%" -LogFile "%LOGFILE%"') do set DISPLAY_ID=%%a

if "%DISPLAY_ID%"=="" (
    timeout /t 1 >nul
    goto esperar_display
)

echo Display detectado: %DISPLAY_ID%
timeout /t 6 >nul
::echo Tocando boton de login...
::adb -s %DEV% shell input -d %DISPLAY_ID% tap 1850 900

:fin
exit /b 0