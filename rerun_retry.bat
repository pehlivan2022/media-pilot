@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONPATH=.

echo === Ripresa: continua il retry da dove si era interrotto ===
echo (lo script salva su disco dopo ogni singolo item: nessun lavoro gia' fatto viene ripetuto)
echo.

python data\golden\retry_deepseek.py

echo.
echo === Fine ===
pause
