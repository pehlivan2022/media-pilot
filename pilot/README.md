# pilot — note operative

## Finestra a 7 giorni: si ottiene solo accumulando

I feed RSS delle fonti sono tappati a ~100 entry. Una singola run di `collect.py` non produce
mai un corpus a 7 giorni: produce al massimo quello che i feed espongono in quel momento (spesso
1 giorno di copertura reale per le fonti ad alto volume). **Il corpus a 7 giorni si ottiene
collezionando per 7 giorni**, non con un parametro `--days` più alto.

`collect.py` fa dedup contro **tutti** i file `data/raw/*.jsonl`, non solo quello del giorno
corrente: gira più volte al giorno senza duplicare.

## Farlo girare periodicamente (Windows Task Scheduler)

Nessun demone: basta un task schedulato ogni 30–60 minuti. Da un terminale con permessi utente
(non serve admin), registrare con `schtasks`:

```
schtasks /create /tn "MediaPilotCollect" /tr "python -m pilot.collect --days 7" ^
  /sc minute /mo 45 /st 00:00 ^
  /sd <data odierna> ^
  /f
```

Da eseguire con working directory sulla root del progetto (`schtasks` non la eredita: usare uno
`.bat` che fa `cd` prima del comando, o `/tr` con path assoluti a `python.exe` e allo script).

Verifica: `schtasks /query /tn "MediaPilotCollect"`. Rimozione: `schtasks /delete /tn "MediaPilotCollect" /f`.
