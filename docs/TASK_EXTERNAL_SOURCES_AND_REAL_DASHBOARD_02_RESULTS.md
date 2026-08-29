# TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02 — RESULTS

Date: 2026-08-29. Chiusura di `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md`, ripresa dopo
interruzione/rate-limit via `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_CONTINUE.md`.

## 1. Stato iniziale (al resume)

- BLOCCO A: due forkin background avevano prodotto `docs/EXTERNAL_SCRAPER_AUDIT_V2.md` e
  `docs/SOURCE_GAPS_AUDIT.md`. Nessun adapter/config scritto.
- BLOCCO B: `docs/DASHBOARD_REAL_DATA_AUDIT.md` e questo file NON esistevano — ma il codice
  frontend (`header.js`, `page-home.js`, `ui.js`) conteneva gia' commenti che citavano §9/§14/§15
  di questo task come implementati. Non era chiaro se il lavoro fosse davvero completo o solo
  parzialmente scritto: verificato in questo giro (§7 sotto).
- Beta Dashboard precedente (`TASK_FINAL_DASHBOARD_BETA_01`): confermata intatta, non riaperta.

## 2. External source audit

6 repository auditati dal vivo (`gh api`/`gh search`, non training data):
`alphap365/open-news`, `fhamborg/news-please`, `RSS-Bridge/rss-bridge`,
`viperdam/zero-cost-news-scraper`, `riad-azz/next-news-api`, `jasonforis/mediafilter-auto-parse`.
Dettaglio completo: `docs/EXTERNAL_SCRAPER_AUDIT_V2.md`.

**Nessun candidato qualifica.**

## 3. Source gaps

10/18 fonti registrate hanno un gap dichiarato (7 `SHORT_HISTORY`, 5 `NO_RSS`, altre categorie
minori) — dettaglio in `docs/SOURCE_GAPS_AUDIT.md`. Nessuno dei 6 candidati esterni offre un
percorso diverso da quanto gia' provato (RSS diretto + Wayback CDX).

## 4. Adapter

Nessuno. Nessun candidato ha superato l'audit (§2), quindi `pilot/external/` non e' stato creato —
esito esplicitamente previsto dal task (§3: "non forzare una scelta debole").

## 5. Baseline vs Pilot

N/A — nessun provider integrato. Vedi §6 (REJECT).

| Metrica | Baseline | Pilot | Delta |
|---|---:|---:|---:|
| — | — | — | N/A: nessun provider da misurare |

## 6. Decisione provider

**REJECT** su tutti e 6 i candidati. Motivazione aggregata in `docs/EXTERNAL_SCRAPER_AUDIT_V2.md`
("Motivazione aggregata"): tutti violano almeno un vincolo hard del progetto (2 dipendenze totali,
niente database, niente framework/microservizi nuovi) o non offrono copertura RS/BiH reale.

## 7. Dashboard real-data audit

Dettaglio completo: `docs/DASHBOARD_REAL_DATA_AUDIT.md`. Riassunto:

- **REAL**: `rassegna.json`, `trending.json`, `signals.json`, `pipeline_health.json` (scritti dalla
  pipeline reale `pilot/run_all.py`), `candidates.json`/`candidates_source.json` (reference reale,
  fonti citate, ma UNUSED — nessuna pagina lo legge).
- **DEMO**: `alerts.json`, `cases.json`, `tasks.json`, `archive.json` — scritti una volta da
  `tools/build-data.js` a partire da uno scenario demo esterno al progetto (v19-large-light), mai
  toccati dalla pipeline reale.
- **Azioni verificate come gia' presenti nel codice** (non riscritte, solo confermate funzionanti):
  le 6 pagine che usano dataset demo (`media`, `eksperti`, `vrh`, `case`, `simulator`, `arhiva`)
  sono fuori dal menu operativo (`header.js`) e mostrano `UI.demoBanner()`; la HOME operativa non
  referenzia mai cases/tasks/alerts/archive.

## 8. Demo separation

- **Menu operativo** (`header.js` `allItems()`): Radar, US, Konkurenti, Teritorij, Ostali — solo le
  5 pagine REAL.
- **DEV/DEMO**: `media.html`, `eksperti.html`, `vrh.html`, `case.html`, `simulator.html`,
  `arhiva.html` — raggiungibili solo via URL diretto, banner `DEMO / DEV — podaci simulirani, nije
  operativni prikaz` in cima a ciascuna (`ui.js` `demoBanner()`).

## 9. Health

`page-home.js` `pipelineStripHtml()` distingue realmente:
- **DATA UNAVAILABLE**: `pipeline_health.json` mancante/illeggibile (`__missing` include
  `pipeline_health`, o file falsy) — mai `ONLINE` come fallback.
- **DEGRADED**: file presente, `sources_failed` (array di source_id) non vuoto.
- **ONLINE**: file presente, `sources_failed` vuoto.

Bug preesistente gia' corretto nel codice: `sources_failed` e' un array (non un numero) quando
`run_all.py` gira con raccolta attiva — il confronto `>0` su un array era sempre falso. Il render
ora usa `Array.isArray(ph.sources_failed) ? ph.sources_failed : []` prima del confronto.

## 10. Responsive

Verificato realmente in questo giro, via server locale (`python -m http.server`, non `file://`) +
misure DOM reali (iframe a viewport fisso, non solo ispezione visiva):

| Larghezza | Overflow orizzontale | Nav | Sezioni HOME renderizzate |
|---:|---|---|---|
| 390px | No (`scrollWidth==clientWidth`) | drawer mobile (`.mobile-nav` visibile, `.navbar` nascosto) | Trending, Da gledati, Ultime vijesti, US, Konkurenti, Teritorij, Ostali |
| 768px | No | drawer mobile ancora attivo (breakpoint desktop e' `>=769`) | idem |
| 1280px | No | sidebar desktop (`.navbar` visibile) | idem |
| 1920px | No | sidebar desktop, misurato sulla finestra reale (non iframe) | idem |

Nessun errore console rilevato al caricamento (`read_console_messages`, `onlyErrors:true`, vuoto).

## 11. Tests

- Backend: `python -m pilot.test_pipeline` → **25/25 PASS** (rieseguito in questo giro).
- Frontend: `_selftest_beta.html`, servito via http reale (non `file://`, contro i JSON reali non
  l'embedded demo) → **13/13 PASS** (rieseguito in questo giro, non solo ispezione codice).
- Console: nessun errore su `index.html` a caricamento normale.

## 12. Limiti residui

- `candidates.json`/`candidates_source.json` e' dato reale ma **non usato da nessuna pagina** —
  nessuna azione richiesta da questo task (§7/§12 riguardano solo rimuovere/marcare demo, non
  aggiungere consumer per dati reali inutilizzati); segnalato per un task futuro se si vuole
  mostrare la lista candidati da qualche parte (es. `go.html`/`eksperti.html` una volta che
  quest'ultima smette di essere demo).
- Le 5 card REVIEW senza codice politico assegnato (gia' note da `FINAL_PROJECT_STATUS.md`) restano
  aperte, invariate da questo task.
- Nessun provider esterno integrato (§6): i 10 gap `SHORT_HISTORY`/`NO_RSS` restano dichiarati, non
  risolti — nessuno dei 6 candidati offriva un percorso valido.
