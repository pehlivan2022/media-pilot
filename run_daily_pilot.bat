@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONPATH=.

rem Lanciato da Task Scheduler (task "MediaPilot_DailyAll", trigger 06:00 + trigger di catch-up
rem 12:00, §1c TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01) — nessuna interazione utente: niente
rem pip install, niente pause, tutto l'output va solo su file di log. Per un lancio manuale con
rem output a video, usa direttamente:
rem   python -m pilot.run_monitor --target pilot_daily_all

set LOGFILE=data\scheduler_run.log

rem rotazione: se il log supera ~5MB, spostalo in .1 (sovrascrive il .1 precedente) e riparti vuoto
if exist "%LOGFILE%" (
    for %%A in ("%LOGFILE%") do set LOGSIZE=%%~zA
    if !LOGSIZE! GTR 5242880 move /Y "%LOGFILE%" "%LOGFILE%.1" >nul
)

rem catch-up idempotente: se il raw di oggi esiste gia' (trigger 06:00 riuscito), il trigger di
rem catch-up delle 12:00 non deve rilanciare da capo la raccolta di rete.
set TODAY=%DATE:~-4%-%DATE:~3,2%-%DATE:~0,2%
if exist "data\raw\%TODAY%.jsonl" (
    echo ============================================== >> "%LOGFILE%"
    echo catch-up %DATE% %TIME%: data\raw\%TODAY%.jsonl gia' presente, run saltato >> "%LOGFILE%"
    echo ============================================== >> "%LOGFILE%"
    endlocal
    exit /b 0
)

echo ============================================== >> "%LOGFILE%"
echo run avviato: %DATE% %TIME% >> "%LOGFILE%"
echo ============================================== >> "%LOGFILE%"

"C:\Users\frontofficedx\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe" -m pilot.run_monitor --target pilot_daily_all >> "%LOGFILE%" 2>&1

echo run terminato: %DATE% %TIME% (exit code %ERRORLEVEL%) >> "%LOGFILE%"
echo. >> "%LOGFILE%"

endlocal
