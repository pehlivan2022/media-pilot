# DASHBOARD REAL DATA AUDIT

Date: 2026-08-29. `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md` §12 / `..._02_CONTINUE.md` §6.
Audit dei file frontend realmente presenti (non quelli elencati a titolo di esempio nel task, che
citava `app.js`, mai esistito in questo repo) e classificazione REAL/DEMO/MIXED/UNUSED di ogni
dataset. Fonte per la classificazione: non un grep per parole chiave (`demo`/`mock`/`fake`), ma il
confronto diretto tra cosa scrive `pilot/run_all.py` (pipeline reale) e cosa consuma ogni pagina —
vedi `pilot/export_dashboard.py` riga 24 (`RASSEGNA_JSON`), `pilot/run_all.py` righe 81-92
(`trending.export_trending_json`, `signals.export_signals_json`, `export_dashboard.export_rassegna`)
contro `data.js` FILES e i vari `page-*.js`.

**Trovato durante l'audit**: `tools/build-data.js` (eseguito a mano una volta, non dalla pipeline)
genera `alerts.json`/`cases.json`/`tasks.json`/`archive.json` a partire da `scenarios.json` +
`archive_cases.json` presi da un progetto DEMO separato
(`...\_____us-demo-media-pilot-v19-large-light\`), non dal pilot reale. `candidates.json` invece
viene generato dallo stesso script ma a partire da `assets/data/candidates_source.json`, scritto a
mano in QUESTO repo con fonti reali datate (vedi nota in testa a quel file) — dato reale di
riferimento, non demo, semplicemente non generato dalla pipeline di raccolta articoli.

---

## Dataset (`assets/data/*.json`, `data/pipeline_health.json`)

| Dataset | Scritto da | Classificazione | Note |
|---|---|---|---|
| `rassegna.json` | `pilot/run_all.py` → `export_dashboard.export_rassegna()` | **REAL** | Da `data/scored_items.jsonl`, pipeline reale |
| `trending.json` | `pilot/run_all.py` → `trending.export_trending_json()` | **REAL** | |
| `signals.json` | `pilot/run_all.py` → `signals.export_signals_json()` | **REAL** | |
| `pipeline_health.json` | `pilot/run_all.py` (fine corsa) | **REAL** | |
| `candidates.json` / `candidates_source.json` | `tools/build-data.js` da fonte scritta a mano con URL/data citati | **REAL** (reference, non pipeline) | **UNUSED** — nessun `page-*.js` legge `data.candidates` |
| `alerts.json` | `tools/build-data.js` da scenario DEMO esterno | **DEMO** | Nessun consumer trovato (nessun `data.alerts` in `page-*.js`) |
| `cases.json` | `tools/build-data.js` da scenario DEMO esterno | **DEMO** | Usato solo da pagine gia' marcate DEMO (vedi tabella pagine) |
| `tasks.json` | `tools/build-data.js` da scenario DEMO esterno | **DEMO** | Idem |
| `archive.json` | `tools/build-data.js` da scenario DEMO esterno | **DEMO** | Idem |

## Pagine / moduli

| File | Dataset usato | Classificazione | Stato nav operativa |
|---|---|---|---|
| `index.html` / `page-home.js` | rassegna, trending, signals | REAL | In menu (Radar) |
| `us.html` / `page-us.js` | rassegna, signals | REAL | In menu (US) |
| `konkurenti.html` / `page-konkurenti.js` | rassegna, signals | REAL | In menu (Konkurenti) |
| `go.html` / `page-go.js` | rassegna, signals | REAL | In menu (Teritorij) |
| `ostali.html` / `page-ostali.js` | rassegna, signals | REAL | In menu (Ostali) |
| `media.html` / `page-media.js` | cases, tasks | **DEMO** | Fuori menu, `UI.demoBanner()` |
| `eksperti.html` / `page-eksperti.js` | tasks | **DEMO** | Fuori menu, `UI.demoBanner()` |
| `vrh.html` / `page-vrh.js` | cases, tasks (via `RadarEngine.alerts()/cases()` sulla catena demo) | **DEMO** | Fuori menu, `UI.demoBanner()` |
| `case.html` / `page-case.js` | cases, tasks | **DEMO** | Fuori menu, `UI.demoBanner()` |
| `simulator.html` / `page-simulator.js` | cases, tasks (+ `Math.random()` per pescare un case a caso) | **DEMO** | Fuori menu, `UI.demoBanner()`; `Math.random` accettabile qui: e' esplicitamente uno strumento dev/demo, non un dato mostrato come operativo |
| `arhiva.html` / `page-arhiva.js` | archive | **DEMO** | Fuori menu, `UI.demoBanner()` |
| `konkurenti.html`, `us.html`, `go.html`, `ostali.html` | — | — | vedi righe REAL sopra |

**Nav operativa reale** (`header.js` `allItems()`): Radar, US, Konkurenti, Teritorij, Ostali — solo
le 5 pagine REAL. Le 6 pagine DEMO restano raggiungibili solo via URL diretto, ciascuna con banner
`DEMO / DEV — podaci simulirani, nije operativni prikaz` in cima (`ui.js` `demoBanner()`).

## Azioni gia' effettuate (trovate in codice, non rifatte in questo giro)

Questo lavoro risultava gia' presente nel repository al momento dell'audit — commentato inline nei
file stessi con riferimento a `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02` §9/§14/§15:

1. `header.js` — le 6 pagine demo rimosse da `allItems()`/`mobilePrimary()`.
2. `page-home.js` — pannello VRH (derivava da `cases.json` demo) rimosso dalla HOME.
3. `ui.js` — `demoBanner()` aggiunto e usato in tutte le 6 pagine demo.
4. `page-home.js` `pipelineStripHtml()` — bug `sources_failed` corretto: gestito come array
   (`Array.isArray(ph.sources_failed)`), non confrontato con `>0` da numero.
5. Tre stati distinti in `pipelineStripHtml()`: DATA UNAVAILABLE (file assente/illeggibile — mai
   `ONLINE` come fallback), DEGRADED (file presente, `sources_failed.length>0`), ONLINE.

## Azioni NON necessarie

- Nessun dataset DEMO alimenta KPI, semafori, conteggi o card nella HOME operativa (verificato:
  `page-home.js` non referenzia mai `data.cases`/`data.tasks`/`data.alerts`/`data.archive`).
- Nessuna card rossa automatica, nessun `Math.random()` fuori dal simulator demo-marcato — vedi
  `_selftest_beta.html` test #13 (55 card, 0 rosse) rieseguito realmente in questo giro, PASS.
