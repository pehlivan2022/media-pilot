# FINAL PROJECT STATUS — MEDIA PILOT / RADAR POLITICO

**Aggiornamento 2026-08-29 (giro più recente)**: `TASK_WINDOWS_SCHEDULER_01` **FATTO** — dettaglio
in `TASK_WINDOWS_SCHEDULER_01_RESULTS.md`. Task Windows `MediaPilot_DailyAll` registrato via
modulo `ScheduledTasks` (schtasks.exe aveva un bug di quoting sul path con spazi, aggirato):
giornaliero 06:00, solo se l'utente è loggato (nessuna password Windows salvata), esegue
`run_daily_pilot.bat` → `python -m pilot.run_monitor --target pilot_daily_all`, log in
`data\scheduler_run.log`. Nessun aumento di frequenza oltre 1×/giorno.

**Aggiornamento 2026-08-29 (giro precedente)**: `TASK_SOURCE_EXPANSION_DAILY_PILOT_01` **FATTO**
— dettaglio in `TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md` +
`SOURCE_EXPANSION_AUDIT_01.{csv,md}` + `SOURCE_PROBLEMS_01.csv`. Fonti attive **18 → 33** (15
promosse su 22 candidate READY, tetto MAX 15 rispettato). `config/monitoring.yaml` ha ora anche
`pilot_daily_all` (tutte le fonti abilitate, 1×/giorno) senza toccare i 5 target esistenti né
`run_monitor.py`. Run reale eseguito, pipeline 25/25 test verdi, nessuna regressione. Trovato (non
corretto, fuori scope) un bug preesistente in `pilot/collect.py::collect_from_html_source`: un
metodo `html_home_links` puro non raccoglie nulla — la fonte attiva `RS_IJ_018` ne è vittima da
prima di questo task. Nessuno scheduler Windows registrato (prossimo task:
`TASK_WINDOWS_SCHEDULER_01`), nessun aumento di frequenza, nessuno scraping social.

**Aggiornamento 2026-08-29 (giro precedente)**: `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02` e'
**CHIUSO** — dettaglio in `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md`. Nessun provider
esterno integrato (6 candidati auditati, tutti REJECT — vincoli hard del progetto). La dashboard
operativa (Radar/US/Konkurenti/Teritorij/Ostali) e' confermata 100% dati reali; le 6 pagine
demo-based (media/eksperti/vrh/case/simulator/arhiva) sono fuori dal menu operativo e marcate con
banner DEMO — vedi `docs/DASHBOARD_REAL_DATA_AUDIT.md`. Backend 25/25, frontend 13/13, responsive
390/768/1280/1920 verificati realmente (non solo ispezione).

---

Date: 2026-08-29. Scritto a chiusura di `MEDIA_PILOT_FINAL_HANDOFF.md` §39 (ordine A-L). A=B=G
gia' fatti in `TASK_BETA_03_RESULTS.md` (non rifatti qui). Copre C-K; L (Archive/workflow)
dichiarato non fatto, con motivo, in fondo. **J (wiring dashboard) e' stato fatto in un giro
successivo** — vedi `TASK_FINAL_DASHBOARD_BETA_01_RESULTS.md` (2026-08-29): `dashboard-config.js`
resta invariato (mapping card gia' corretto), ma `radar.js`/`ui.js`/`data.js`/`page-home.js` e le
4 pagine card sono stati aggiornati per leggere `rassegna.json`/`trending.json`/`signals.json`/
`pipeline_health.json` reali — semafori grigio/verde/ambra derivano ora da Signal REVIEW reali
(mai rosso automatico), non piu' dalla catena demo `alerts()/cases()`.

**FERMATO qui** come richiesto ("solo quando il sistema completo puo' essere eseguito e
aggiornare la dashboard in modo ripetibile") — vale per i JSON; per la UI vedi la nota su J sopra.

---

## Cosa funziona

Un comando solo rigenera tutto e produce i tre JSON reali:

```bash
python -m pilot.run_all                # con raccolta di rete
python -m pilot.run_all --no-collect   # riusa data/raw/ gia' presente
```

Catena: `collect -> clean -> entities -> dedup -> score -> trending -> signals -> export_dashboard`,
si ferma al primo stadio che produce zero, scrive `data/pipeline_health.json` a fine corsa.
Ultima esecuzione completa misurata: **253,9 secondi** su 2.267 item puliti.

| stadio | output |
|---|---:|
| clean | 2.267 |
| dedup | 1.947 |
| cluster | 462 |
| rassegna (item rilevanti) | 683 |
| con card dashboard | 471 = 69% |
| entita' nel registry con Trending | 55 |
| entita' attive (24h) in `trending.json` | 24 |
| Signal candidati | 24 (17 REVIEW, 7 MONITORING) |
| test | **25/25** |

`config/monitoring.yaml` (nuovo): dichiara COSA monitorare (entita', fonti) e QUANTO SPESSO, per
target — letto da `pilot/run_monitor.py`.

---

## Cosa resta manuale

- **Scheduler effettivo**: nessun cron/Task Scheduler configurato su questa macchina (§9
  dell'handoff lo vieta implicitamente: "non costruire un orchestratore interno complesso", e
  creare voci di scheduling di sistema e' un'azione sulla macchina dell'utente, non presa senza
  chiedere). Vedi "Istruzioni operative" sotto per i comandi esatti da mettere in Task Scheduler.
- **Le 5 card REVIEW** (`predsjednistvo`, `finansiranje`, `sps`, `sp-demos`, `dns-nps`, audit in
  `TASK_BETA_03_RESULTS.md` D2.1): nessun codice politico assegnato — richiede una decisione umana
  che il config strutturato non permette di dedurre in sicurezza (vietato esplicitamente:
  "non dedurre codici politici solo dal nome della card").
- **Alert, Case, Task, Decision**: non costruiti (§L, esplicitamente rimandato dall'handoff a
  "solo dopo che Rassegna/Trending/Signal funzionano" — ora funzionano, ma costruire il workflow
  umano/UI e' lavoro separato, non richiesto in questo giro).
- **Wiring dei semafori/detail view ai dati reali** (§J): **fatto** in
  `TASK_FINAL_DASHBOARD_BETA_01_RESULTS.md` (2026-08-29, giro successivo a questa sessione —
  quel vincolo "no frontend rewrite" valeva solo per QUESTA sessione, non per il progetto).
  `radar.js`/`ui.js`/`data.js`/`page-home.js` e le 4 pagine card ora scrivono/leggono i JSON
  reali; `dashboard-config.js` resta invariato (il mapping card era gia' corretto).
  `data/rassegna_preview.html`/`data/trending_signals_preview.html` restano come prova
  indipendente, non piu' l'unico modo di vedere i dati reali.
- **Cross-reference Engine "storico"** (OHR↔NSRS↔STE ecc., da `MEDIA_PILOT_NEXT_TASKS_AFTER_BETA02.md`
  E2/E3): **non costruito**. `config/crossrefs_seed_ids.json` citato in quel documento non esiste
  nel repo. `MEDIA_PILOT_FINAL_HANDOFF.md` (piu' recente, ha sostituito l'ordine dei lavori) elenca
  "cross-reference" solo come uno dei possibili INPUT del Signal Engine, non come motore separato:
  implementato come co-occorrenza di entita' nello stesso articolo/evento (`max_co_entities_in_event`,
  gia' misurato da `pilot/entity_salience.py`) invece di un sistema di relazioni configurate a
  parte — piu' semplice, nessuna nuova astrazione, coerente con "no overengineering".

---

## Configurazione scheduler (dichiarativa, non un orchestratore)

`config/monitoring.yaml`, 5 target, tutti `enabled: true`:

| target | priorita' | runs/day | fonti | entita' |
|---|---|---:|---:|---:|
| us_core | high | 12 | 4 | 4 |
| doboj | high | 8 | 3 | 4 |
| institutions | medium | 6 | 4 | 5 |
| opposition_competitors | medium | 6 | 4 | 7 |
| background | low | 3 | 5 | (nessuna, copertura generale) |

`pilot/run_monitor.py --priority high|medium|low` e/o `--target <id>` risolve l'unione delle
fonti dei target richiesti (una fonte condivisa da piu' target si raccoglie una sola volta,
`test_17`) e lancia `run_all.run()` limitato a quelle fonti. Il resto della pipeline (clean/dedup/
score/trending/signals/export) gira sempre per intero — non si puo' deduplicare/clusterizzare un
sottoinsieme senza il resto del corpus come contesto.

---

## Fonti attive

18 fonti abilitate in `config/sources.yaml` (17 gia' verificate + Capital.ba via Wayback CDX,
B2a). Nessuna disabilitata in questo giro. `window_actual_days` per fonte aggiornato
automaticamente ad ogni `collect()` (min 0 — `RS_IJ_018`/InfoBijeljina, 0 giorni nella finestra
corrente — max 27 — `BL_IJ3_002`/Nezavisne). Mediana fonti attive/giorno: **5,5** (invariata da
`TASK_BETA_03_RESULTS.md`: il secondo giro di backfill ha aggiunto volume, non giorni, su queste
fonti — limite dichiarato, non forzato).

---

## JSON reali prodotti (schema in `docs/dashboard-data-contract.md`)

- `assets/data/rassegna.json` — 683 item rilevanti, invariato da Beta 02/03.
- `assets/data/trending.json` — **NUOVO in questo giro**, 24 entita' con `mentions_24h/
  unique_events_24h/unique_sources_24h/baseline_7d/momentum/last_event_at/top_events/evidence`,
  tutti reali. Schema per-ENTITA', non per-articolo (nota architetturale in `pilot/trending.py`).
- `assets/data/signals.json` — **NUOVO in questo giro**, 17 SignalCandidate REVIEW con
  `why_now/entities/events/metrics/sources/evidence/confidence/provenance`. Nessun Alert/Case.
- `data/pipeline_health.json` — **NUOVO**, stato scraper (last_run, sources_ok/failed quando
  `do_collect=True`, conteggi per stadio, durata).
- File interni per audit, non dashboard-facing: `data/trending_entities.jsonl` (55 righe, tutto il
  registry), `data/entity_salience.jsonl` (1.766 righe, item×entita'), `data/signal_candidates.jsonl`
  (24 righe, MONITORING+REVIEW).

`alerts.json`/`cases.json`/`tasks.json`/`archive.json`/`candidates.json` **non toccati**: restano
demo (`tools/build-data.js`), dichiarato in `dashboard-data-contract.md` per non mescolare dati
demo e reali senza marcarli (§38).

---

## Test

`python -m pilot.test_pipeline` → **25/25 verdi** (era 20/20 a fine Beta 02; +5 in questa
sessione complessiva: `test_4b` D0.1, `test_14`/`test_15` D1/D2.2, `test_16` Signal Candidate,
`test_17` run_monitor).

---

## Limiti noti (dichiarati, non nascosti)

- **`signal_score` resta a 22 valori distinti** su 462 cluster — tetto reale dei 4 segnali
  osservabili su questo corpus (81%+ singoletti), non un difetto di calibrazione. Non toccato in
  questo giro (regola esplicita: "no thresholds changed just to pass KPI").
- **`baseline_7d`/`momentum` quasi sempre al minimo misurabile** per la maggior parte delle
  entita': su un corpus di 683 item rilevanti, 55 entita' non riempiono una settimana di bucket.
  Il numero e' reale, non e' pero' ancora "un ritmo consolidato" nel senso pieno del termine.
- **Le soglie del Signal Engine sono dichiarate, non calibrate**: `REVIEW_CONFIDENCE_MIN=0.6`,
  `MOMENTUM_SIGNAL_MIN=0.5` ecc. (`pilot/signals.py`) sono un punto di partenza esplicito, non
  tarato su un golden set di Signal umanamente confermati (non esiste ancora). Misurato: su questo
  corpus il 71% dei candidati con attivita' finisce REVIEW — probabile segno che le soglie sono
  permissive durante una campagna elettorale densa, non necessariamente un errore. Non retoccate
  qui per non violare la stessa regola di sopra.
- **BL_IJ3_006 (Banjaluka24)**: contaminazione widget corretta (D0.1, 71,4%→0%). Resta un rischio
  residuo diverso e non affrontato: quella fonte e' comunque a bassa diversita' editoriale interna
  (un solo portale locale), non ricontrollato in questo giro.
- **RTRS (RS_ENT_001)** resta a 2 giorni di storia: nessun metodo HTTP stabile trovato (audit in
  `TASK_BETA_03_RESULTS.md`), dichiarato, non forzato con browser automation (vietato).

---

## Istruzioni operative

**Rigenerare tutto** (raccoglie di rete, richiede qualche minuto):
```bash
python -m pilot.run_all
```

**Rigenerare solo dai dati gia' raccolti** (utile dopo una modifica a `config/scoring.yaml` o
`dashboard-config.js`, ~4 minuti sul corpus attuale):
```bash
python -m pilot.run_all --no-collect
```

**Raccolta mirata per priorita'/target** (per uno scheduler esterno con frequenze diverse):
```bash
python -m pilot.run_monitor --priority high
python -m pilot.run_monitor --target doboj
```

**Esempio Windows Task Scheduler** (l'utente lo crea, non fatto automaticamente da questa
sessione): un'azione `pythonw -m pilot.run_monitor --priority high` ogni 2h nella fascia
06:00-24:00, una seconda `--priority medium` ogni 4h, una terza `python -m pilot.run_all
--no-collect` una volta al giorno per rigenerare trending/signal/rassegna sull'intero corpus dopo
l'ultima raccolta parziale (`run_monitor` raccoglie solo le fonti del target, ma clean/dedup/
score/trending/signals girano gia' per intero ad ogni chiamata — non serve un passo separato se
si usa sempre `run_monitor`, il comando extra serve solo per una rigenerazione esplicita a freddo).

**Guardare i dati prima della dashboard**: aprire `data/rassegna_preview.html` e
`data/trending_signals_preview.html` (nessun server necessario, file locali autosufficienti).

**Test**: `python -m pilot.test_pipeline` (o `pytest pilot/`).
