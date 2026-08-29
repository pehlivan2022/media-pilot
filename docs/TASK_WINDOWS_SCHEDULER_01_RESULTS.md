# TASK_WINDOWS_SCHEDULER_01 — RESULTS

**Stato: FATTO, 2026-08-29.** Registrato lo scheduler di sistema per `pilot_daily_all`, come
indicato come prossimo passo naturale in `TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md`.

## Cosa è stato registrato

- **Task**: `MediaPilot_DailyAll` (Windows Task Scheduler, root `\`).
- **Trigger**: giornaliero, `06:00` locale, `DaysInterval: 1`.
- **Azione**: `run_daily_pilot.bat` (nuovo, alla radice del repo), working directory = radice del
  repo.
- **Comando eseguito dal bat**:
  `python -m pilot.run_monitor --target pilot_daily_all` (lo stesso identico comando già validato
  con un run reale in `TASK_SOURCE_EXPANSION_DAILY_PILOT_01`), con Python invocato tramite il suo
  path assoluto risolto (`...\WindowsApps\PythonSoftwareFoundation.Python.3.12_qbz5n2kfra8p0\python.exe`)
  invece dell'alias `python` di PATH, per evitare ambiguità quando gira fuori da una sessione
  interattiva.
- **Utente**: `frontofficedx`, `LogonType: Interactive`, `RunLevel: Limited` — **gira solo se sei
  loggato in Windows** (scelta esplicita dell'utente): nessuna password salvata da Task
  Scheduler. Se il PC è spento o l'utente è sloggato alle 06:00, quel giorno il run salta (nessun
  recupero automatico — va rilanciato a mano con `python -m pilot.run_monitor --target
  pilot_daily_all`, oppure aspettare il giorno dopo).
- **Log**: ogni run appende a `data\scheduler_run.log` (timestamp inizio/fine + tutto lo stdout/
  stderr del comando, incluso quanto già visto nel run manuale: collect → clean → dedup → score →
  trending → signals → export_dashboard). File append-only, nessuna rotazione — da controllare/
  pulire manualmente se cresce troppo nel tempo.

## Come verificarlo

```powershell
Get-ScheduledTask -TaskName "MediaPilot_DailyAll" | Get-ScheduledTaskInfo
```

oppure aprire "Utilità di pianificazione" di Windows e cercare `MediaPilot_DailyAll`.

Per un run manuale immediato (senza aspettare le 06:00), da riga di comando nella cartella del
progetto:

```
run_daily_pilot.bat
```

oppure, con output a video invece che solo su file:

```
python -m pilot.run_monitor --target pilot_daily_all
```

## Nota tecnica (per chi tocca questo task in futuro)

La registrazione con `schtasks /create /tr "<path con spazi>"` da PowerShell **non ha funzionato
in modo affidabile**: il quoting del percorso (che contiene spazi, es. "NIK 2026") veniva
troncato al primo spazio, spezzando l'azione in un eseguibile inesistente + argomenti — verificato
due volte, con e senza quoting manuale del path. Risolto passando ai cmdlet nativi del modulo
`ScheduledTasks` (`New-ScheduledTaskAction`/`New-ScheduledTaskTrigger`/
`New-ScheduledTaskPrincipal`/`Register-ScheduledTask`), che costruiscono l'azione come oggetto
COM invece che come stringa da riparsare — nessun problema di quoting. Verificato con
`Get-ScheduledTask ... | Select Actions` che `Execute` contenga il path intero e `Arguments` sia
vuoto, prima di dichiarare il task pronto.

## Cosa NON è stato fatto (fuori scope)

- Nessun aumento di frequenza oltre 1×/giorno (§26/§27 del task precedente restano validi).
- Nessuna esecuzione "anche se sloggato" (avrebbe richiesto salvare la password Windows
  dell'utente — scelta esplicita dell'utente di non farlo).
- Nessuna rotazione/pulizia automatica di `data\scheduler_run.log`.
- Nessun alert/notifica se il run fallisce — solo il log su file. Se serve, prossimo task
  separato (fuori scope qui, per non introdurre un secondo orchestratore).
