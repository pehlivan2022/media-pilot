@echo off
rem FASE 2 passo 2: serve la dashboard via HTTP solo per installarla come app (icona sulla home
rem dello smartphone) — richiesto perche' un service worker non si registra su file://. Il
rem doppio click su index.html continua a funzionare come sempre, questo script e' opzionale.
cd /d "%~dp0"
echo Media Pilot su http://localhost:8000 - CTRL+C per fermare.
start "" http://localhost:8000/index.html
python -m http.server 8000
