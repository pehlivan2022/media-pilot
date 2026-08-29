# TASK_SOURCE_EXPANSION_DAILY_PILOT_01 — RESULTS

**Stato: FATTO, 2026-08-29.** Dettaglio completo dell'audit in `docs/SOURCE_EXPANSION_AUDIT_01.md`
+ `.csv`, problemi tecnici in `docs/SOURCE_PROBLEMS_01.csv`. Questo file riassume solo l'esito
rispetto alla definition of done del task originale.

## Cosa è stato fatto, in ordine

1. **Input copiati** in `input/source_candidates/` (v14 xlsx, v12 csv, v13 xlsx+csv, v11 xlsx,
   facebook_urls_verificati_2.xlsx, social_ok_.xlsx, Cvije xlsx). File mancante rispetto
   all'elenco del task: `aebcdd74-f407-4026-be79-9dcc7f59d46a.xlsx` — non trovato in `US/IZVORI/`
   né altrove sul disco, registrato come input mancante, nessuna azione bloccante (era comunque
   solo cross-check).
2. **Baseline catturata prima di ogni modifica**: `python -m pilot.test_pipeline` → 25/25 verdi,
   `data/pipeline_health.json` letto (18 fonti, clean 2.267, dedup 1.947, cluster 462, rassegna
   683, signal REVIEW 17, 251,6s).
3. **Diff per canonical domain**: 18/110 già attive, 0 ID conflict, 2 senza `website_url`.
4. **Script di audit** scritto: `pilot/source_audit_v14.py` — riusa gli helper HTTP esistenti di
   `pilot/sources.py` (`try_feed`/`try_sitemap`/`robots_allows`/`try_html_from_urls`), **non
   chiama mai `write_sources_yaml()`** (avrebbe cancellato le 18 righe esistenti e la loro
   provenance) e non tocca nessuno dei 7 file pipeline vietati dal task.
5. **51 candidati testati dal vivo** (6 tier-1 gap + 45 tier-2 mirati sulle categorie del §7).
   Tier 3 non testato (nessun gap residuo, budget non speso per policy). Vedi audit per il
   dettaglio completo status-per-status.
6. **15 fonti promosse** in `config/sources.yaml` (18 → 33), scelte tra i 22 candidati
   `READY_RSS`/`READY_SITEMAP` — gli unici due metodi che `pilot/collect.py` sa davvero
   raccogliere. 6 candidati tecnicamente `READY_HTML` (solo homepage-link) **non promossi**:
   dimostrato dal vivo che `pilot/collect.py::collect_from_html_source` non raccoglie nulla per
   un metodo che non contenga `sitemap`/`wayback` (prova: la fonte già attiva `RS_IJ_018` con
   quello stesso metodo ha raccolto 0 item nel run reale — registrato come
   `REGRESSION_EXISTING_SOURCE`, preesistente, non toccato per §22).
7. **`config/monitoring.yaml`**: aggiunto target `pilot_daily_all` (tutte le 33 source_id
   abilitate, `runs_per_day: 1`, `history_days: 7`) **senza toccare** `run_monitor.py` (lo schema
   esistente lo supportava già via `--target`) né i 5 target esistenti.
8. **Run reale eseguito**: `python -m pilot.run_monitor --target pilot_daily_all` — exit 0,
   pipeline completa (collect → clean → entities → dedup → score → trending → signals →
   export_dashboard), nessuno stadio a zero item.
9. **Test suite ri-eseguita dopo le modifiche**: `python -m pilot.test_pipeline` → **25/25 verdi**
   (uguale al pre-esistente, nessuna regressione).
10. **Report finali scritti**: questo file + `SOURCE_EXPANSION_AUDIT_01.{csv,md}` +
    `SOURCE_PROBLEMS_01.csv`.
11. **Status doc aggiornati**: `FINAL_PROJECT_STATUS.md`, `HANDOFF_PROGRESS.md`.

## Numeri chiave

| | prima | dopo |
|---|---:|---:|
| fonti attive | 18 | 33 |
| clean | 2.267 | 3.623 |
| dedup | 1.947 | 2.957 |
| cluster | 462 | 613 |
| rassegna | 683 | 1.065 |
| signal REVIEW | 17 | 20 |
| test suite | 25/25 | 25/25 |

## Cosa NON è stato fatto (deliberatamente, per lo STOP condition del task §32)

- **Nessuna registrazione di Windows Task Scheduler.** `pilot_daily_all` è pronto ma non
  schedulato — sarà `TASK_WINDOWS_SCHEDULER_01`.
- **Nessun aumento di frequenza oltre 1×/giorno.**
- **Nessuno scraping social** (Facebook/Instagram/X usati solo come metadata/provenance nella
  v14, mai raccolti).
- **Nessun browser headless** introdotto per le 4 fonti `JS_ONLY`.
- **Nessuna modifica** a `pilot/clean.py`, `dedup.py`, `score.py`, `trending.py`, `signals.py`,
  `run_all.py`, `run_monitor.py` — solo `config/sources.yaml`, `config/monitoring.yaml` e il
  nuovo `pilot/source_audit_v14.py` (script di audit, non pipeline).
- **Nessun fix** al bug dimostrato in `pilot/collect.py::collect_from_html_source`
  (dispatch `sitemap`/`wayback`-only) — fuori scope per questo task, solo documentato.
- **Nessun backfill storico massiccio** sulle 15 nuove fonti: `history_days: 7` nel profilo
  daily, non 30 come i target esistenti già consolidati.

## Correzione fatta in revisione (prima di dichiarare FATTO)

`pilot_daily_all` era stato scritto con `priority: low`. Bug trovato in revisione: `run_monitor.py
resolve_source_ids` unisce i target per `priority`, quindi `python -m pilot.run_monitor --priority
low` avrebbe silenziosamente unito `background` (5 fonti, 3×/giorno) con `pilot_daily_all` (33
fonti) — il job low-priority esistente sarebbe passato a girare le 33 fonti fino a 3 volte al
giorno, violando il §26 ("NON deve aumentare la frequenza oltre 1×/giorno"). Corretto impostando
`priority: pilot` (valore fuori da `high|medium|low`, gli unici accettati da `--priority` in
`run_monitor.py`): ora `pilot_daily_all` è raggiungibile **solo** con `--target pilot_daily_all`,
verificato con `resolve_source_ids` prima e dopo la correzione.

## Prossimo passo naturale

`TASK_WINDOWS_SCHEDULER_01` (o cron equivalente) per registrare
`python -m pilot.run_monitor --target pilot_daily_all` 1×/giorno. Dopo qualche giorno di run
stabili, valutare se dividere `pilot_daily_all` per priorità (high/medium/low) come già fatto
per gli altri target, secondo il criterio del §27 (non implementato ora, intenzionalmente).

STOP.
