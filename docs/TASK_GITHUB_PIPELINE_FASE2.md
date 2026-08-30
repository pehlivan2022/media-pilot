# TASK — GitHub Pipeline FASE 2 (ricostruito)

**Nota**: il task originale di questa fase è stato dato in chat in una sessione precedente e non è
mai stato salvato come file — `docs/GITHUB_PIPELINE_RUNTIME_AUDIT.md` lo cita ("punto 2", "punto
13"), quindi aveva almeno 13 punti numerati. Questo file **ricostruisce** solo ciò che serve dai
riferimenti nell'audit + dallo stato del repo, non è un recupero testuale. Se qualche punto originale
manca, va segnalato dall'utente confrontando con quello che ricorda.

## Punti ricostruiti

1. **Persistenza dello stato fra run.** `data/raw/*.jsonl` è l'unico stato necessario (verificato in
   `collect.py`, vedi audit). Attualmente in `.gitignore` (`data/*`), quindi su una VM Actions
   effimera andrebbe perso ad ogni run. **Deciso dall'utente**: raw completo (non solo id), su un
   branch dedicato `runtime-state` nello stesso repo pubblico — testo articoli esposto in chiaro,
   accettato consapevolmente per mantenere l'accumulo a 30gg identico al comportamento locale.
2. **Portabilità Windows → Linux.** Verificato in questa sessione: nessun blocco nei file toccati da
   `run_all.py`. Unico path Windows hardcoded trovato è `pilot/sources.py:21`
   (`C:\Users\...\NIK 2026\...csv`), ma quel modulo non è importato da nessuno degli 8 stadi
   (solo `pilot/source_audit_v14.py` lo usa, tool manuale fuori scope) — nessuna modifica necessaria.
   `entities.py` legge `dashboard-config.js` come testo puro (regex), niente `node`/subprocess.
3. **Dipendenze.** `requirements.txt` = `feedparser`, `trafilatura`. `pandas` è usato solo da
   `source_audit_v14.py` (fuori scope). Lo yaml è letto da un parser interno (`pilot/miniyaml.py`),
   niente `pyyaml` esterno. Nessuna dipendenza Windows-only.
4. **Workflow GitHub Actions per la pipeline.** `.github/workflows/daily-pipeline.yml`: checkout
   codice + branch `runtime-state` → ripristina `data/raw/*.jsonl` + `errors.jsonl` → `pip install`
   → `python -m pilot.run_monitor --target pilot_daily_all` → commit nuovo stato su `runtime-state`
   → commit output dashboard su `master`.
5. **Deploy.** `.github/workflows/publish-pages.yml` esteso con trigger `workflow_run` (parte da solo
   dopo un run riuscito di "Daily Pipeline", oltre al `workflow_dispatch` manuale esistente) —
   nessuna duplicazione dei ~170 righe di build/validate/verify già presenti.
6. **Trigger/scheduler.** `daily-pipeline.yml` ha `workflow_dispatch` + due `schedule:` cron
   (`0 5 * * *`, `0 11 * * *` UTC ≈ 06:00/12:00 Europe/Sarajevo), a sostituire Task Scheduler locale
   + catch-up. `run_daily_pilot.bat`/Task Scheduler locale restano come fallback manuale, non
   cancellati.
7. **Secrets `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`.** **Non necessari.** Verificato nell'audit
   (Scoperta critica 1): nessuno degli 8 stadi importa `pilot/llm.py`. Nessuna azione — non toccare
   `.env`, non usare `gh secret set`.
8. **Validation gate + deploy.** Già costruiti in `.github/workflows/publish-pages.yml` (step
   "Validate JSON payloads" + job `verify` con checksum). Riusati as-is dal punto 5.
9. **Test dei 2 run.** Dispatch manuale due volte di seguito (`daily-pipeline.yml`, poi verificare
   che `publish-pages.yml` parta da solo). Verifica: il raw del run 2 cresce di circa un giorno di
   item (non un ri-collect completo), confrontando i conteggi in `data/pipeline_health.json`.

## Incidente durante l'esecuzione (2026-08-31)

`git clean -fdx` eseguito per errore durante la creazione del branch orfano `runtime-state` ha
cancellato in modo irreversibile (mai tracciati, `.gitignore: data/*`): `data/raw/2026-08-28/29/30.jsonl`,
`data/errors.jsonl`, `data/golden_b3/`, `data/baseline_20260827/`, `.env` (chiavi API). Recupero
parziale da una sessione parallela in `Desktop\media-pilot-RECUPERO-2026-08-31\` (golden/, fixtures/,
raw/2026-08-27.jsonl parziale). `.env` ricostruito a mano dall'utente con nuove chiavi. Il branch
`runtime-state` viene ricreato da zero via plumbing git (no checkout/clean nel working tree
principale) per evitare di ripetere l'incidente.

## Fuori scope (confermato dall'audit)

- `corpus.db`, `pilot/ask.py`, `pilot/index.py` (RAG) — sottosistema separato.
- `data/golden*/`, `data/fixtures/`, `data/baseline_20260827/` — dataset di test, non toccati da
  `run_all.py`.
