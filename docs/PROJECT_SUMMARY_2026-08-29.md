# PROJECT SUMMARY — 2026-08-29 (verificato contro codice, non narrato)

Ogni numero qui sotto viene da un comando eseguito davvero in questa sessione, citato accanto.

## 1. Pipeline, stadio per stadio

`collect → clean → dedup(+cluster) → score → trending → signals → export_dashboard`, tutta
orchestrata da `pilot/run_all.py` (`python -m pilot.run_all` o `--no-collect`), o dal sottoinsieme
di fonti scelto da `pilot/run_monitor.py --target/--priority`.

Ultimo stato reale registrato in `data/pipeline_health.json` (run del 2026-08-29T02:51:27Z,
`duration_sec: 2685.3` ≈ 44.75 min):

| stadio | valore |
|---|---:|
| fonti abilitate | 33 |
| fonti OK / fallite | 19 / 14 |
| item nuovi in questo run | 1.909 |
| clean (totale) | 3.623 (ora su disco: 3.712 righe `data/clean.jsonl`) |
| dopo dedup | 2.957 (`data/items.jsonl`, `data/scored_items.jsonl`) |
| cluster | 613 (`data/clusters.jsonl`, `data/scored_clusters.jsonl`) |
| rassegna (item con card dashboard) | 1.065 → `assets/data/rassegna.json` (verificato: 1.065 oggetti) |
| entità nel registry Trending | 55 (`data/trending_entities.jsonl`) |
| entità attive (24h) | 26 → `assets/data/trending.json` (verificato: 26 oggetti) |
| Signal candidati totali | 26 (`data/signal_candidates.jsonl`) |
| Signal REVIEW | 20 → `assets/data/signals.json` (verificato: 20 oggetti) |
| test | **25/25 verdi** (`python -m pytest pilot/test_pipeline.py`, appena eseguito) |

**14 fonti su 33 sono fallite nell'ultimo run misurato** (`sources_failed` in
`pipeline_health.json`): `BIH_ELEC_002, BL_IJ3_002, BL_IJ3_003, BL_IJ3_006, BL_IJ3_007, ECO_001,
ECO_002, FBIH_002, FBIH_003, RS_ENT_001, RS_IJ_002, RS_IJ_009, RS_IJ_018, RS_IJ_030` — quasi la metà
delle fonti attive. Non investigato in questa sessione (fuori scope FASE 0), ma è un fatto misurato
da riportare, non un'impressione.

## 2. `config/` — cosa c'è, chi lo scrive

| file | scritto da | note |
|---|---|---|
| `sources.yaml` | script (`pilot/sources.py`, `pilot/source_audit_v14.py`) | 33 righe `enabled: true` (contate: `grep -c "enabled: true"`) |
| `entities.yaml` | script (`pilot/entities.py`), commento "NON modificare a mano" | 55 entità, sorgente `dashboard-config.js` |
| `topics.yaml` | manuale | dizionario di dominio per il filtro di rilevanza |
| `scoring.yaml` | manuale, con commenti che documentano ogni calibrazione (B3.2 ecc.) | soglie dedup/clustering |
| `monitoring.yaml` | **manuale**, commento esplicito "un solo file leggibile e modificabile a mano" | 6 target: `us_core, doboj, institutions, opposition_competitors, background, pilot_daily_all` — letto confermato riga per riga, `priority: pilot` sull'ultimo target è deliberatamente fuori da `high/medium/low` per una proprietà di sicurezza di `argparse choices` (commento in-file, riga 136-139) |

`config/pricing.yaml` **non esiste**. `pilot/spend.py`, `pilot/manage.py`, `data/spend.jsonl`
**non esistono** — verificato (`ls` fallisce su tutti e quattro). Confermano quanto dice il task:
la contabilità spese e il gestore fonti/keyword sono da costruire da zero.

## 3. Dashboard: contratto dati e stato demo/reale

Architettura confermata leggendo `data.js`: fetch su `assets/data/*.json`, fallback su
`window.__MP_EMBEDDED__` (`embedded-data.js`) se il fetch fallisce — funziona anche via `file://`
doppio click, nessun backend.

Contratto in `docs/dashboard-data-contract.md`, verificato contro i file reali:

| file | stato | verifica |
|---|---|---|
| `rassegna.json` | **reale** | 1.065 oggetti, scritto da `pilot/export_dashboard.py` |
| `trending.json` | **reale** | 26 oggetti-entità, scritto da `pilot/trending.py` |
| `signals.json` | **reale** | 20 SignalCandidate REVIEW, scritto da `pilot/signals.py` |
| `pipeline_health.json` | **reale** | stato ultimo run, alimenta la card di stato |
| `alerts.json`, `cases.json`, `tasks.json`, `archive.json`, `candidates.json`, `candidates_source.json` | **demo** | dichiarato nel contratto (`tools/build-data.js`), presente anche `rassegna.json.demo-backup` come prova della migrazione da demo a reale |

## 4. Scheduler `MediaPilot_DailyAll`

Registrato (modulo PowerShell `ScheduledTasks`, non `schtasks.exe` — bug di quoting noto),
giornaliero 06:00, `RunLevel: Limited`, nessuna password salvata, comando
`python -m pilot.run_monitor --target pilot_daily_all` via `run_daily_pilot.bat`.

**Verificato ora con `Get-ScheduledTaskInfo`**: `LastRunTime: 29/08/2026 06:00:00`,
`LastTaskResult: 3221225786` (0xC000013A, `STATUS_CONTROL_C_EXIT` — processo terminato/interrotto).
`data/scheduler_run.log` contiene solo 3 righe ("run avviato: 29/08/2026 6:00:00") seguite da un
carattere `^C` letterale nel file e **nessuna riga "run terminato"** — il bat non ha mai raggiunto
la fine. `pipeline_health.json` risulta ancora fermo a un run manuale precedente (02:51:27Z, prima
delle 06:00), non aggiornato dal run schedulato.

**Divergenza rispetto a `HANDOFF_PROGRESS.md`**, che chiedeva di "verificare domattina che il primo
run automatico sia andato a buon fine": **non è andato a buon fine**, è stato interrotto. Questo è
esattamente il tipo di buco che la FASE 1c del task chiede di colmare (nessun recupero, nessuna
notifica di fallimento) — non un'ipotesi, un fatto già accaduto stamattina.

I tre buchi noti restano tutti presenti e verificati: gira solo se loggato, nessun catch-up se il
PC è spento, `scheduler_run.log` append-only senza rotazione (oggi minuscolo, 3 righe, ma senza
meccanismo di rotazione nel codice).

## 5. Cosa resta aperto

- **Contaminazione temporale (B1)**: risolta a livello di filtro (`pilot/clean.py:out_of_window`),
  ma i tre criteri B1 (bucket 4h, giorno dominante, novelty) restano FAIL per costruzione/densità
  del corpus — dichiarato non bloccante, non richiede altro codice secondo `B1_RESULTS.md`.
- **BL_IJ3_006/Banjaluka24**: bug di estrazione `trafilatura` (~71% item contaminati), non
  corretto — e compare di nuovo nell'ultimo run come fonte fallita.
- **Le 5 card REVIEW** senza codice politico assegnato: decisione umana esplicitamente rimandata.
- **Alert/Case/Task/Decision/Archive**: non costruiti, per scelta esplicita di progetto.
- **Cross-reference "storico"**: non costruito come motore separato, implementato solo come
  co-occorrenza entità (scelta dichiarata, non un buco).
- **Run schedulato interrotto stamattina** (§4): da investigare, non è nel perimetro della FASE 0
  ma è un fatto nuovo rispetto a quanto i documenti di handoff assumevano.

## Divergenze doc ↔ codice

1. **`HANDOFF_PROGRESS.md` assume il primo run schedulato andato a buon fine**: falso, verificato
   (§4) — interrotto con `STATUS_CONTROL_C_EXIT`, log incompleto, `pipeline_health.json` non
   aggiornato dal run delle 06:00.
2. **Conteggi**: i documenti (`FINAL_PROJECT_STATUS.md`) citano l'ultimo run con rassegna 683 item /
   471 con card; il run più recente misurato ora (`pipeline_health.json`, 2026-08-29T02:51) ne ha
   1.065 — coerente con l'espansione fonti (18→33) intervenuta dopo la scrittura di quel documento,
   non una contraddizione ma un dato invecchiato: il documento non è stato aggiornato dopo l'ultimo
   run reale.
3. Nessuna altra divergenza sostanziale trovata tra le affermazioni di `pilot/` (codice) e i numeri
   citati nei report più recenti (`TASK_WINDOWS_SCHEDULER_01_RESULTS.md`,
   `TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md`) — quei due risultano accurati contro il
   codice attuale.
