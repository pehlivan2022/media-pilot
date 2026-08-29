@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONPATH=.

echo === Primo avvio: retry annotazioni DeepSeek fallite (golden set) ===
echo.
echo Verifico/installo le dipendenze (feedparser, trafilatura)...
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo ERRORE: pip install fallito. Verifica che Python sia installato e nel PATH.
  pause
  exit /b 1
)

if not exist ".env" (
  echo ATTENZIONE: manca il file .env nella cartella del progetto.
  echo Copialo dal PC originale prima di continuare - senza non trova le chiavi API.
  pause
  exit /b 1
)

echo.
echo Avvio... ogni item impiega circa 50-60 secondi, e' normale che sembri fermo.
echo Se questa finestra si chiude o il PC si spegne, rilancia rerun_retry.bat: riprende da dove era rimasto.
echo.

python data\golden\retry_deepseek.py

echo.
echo === Fine ===
pause
