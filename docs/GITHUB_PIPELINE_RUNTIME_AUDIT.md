# GitHub Pipeline Runtime Audit (FASE 2, punto 1)

Data: 2026-08-30. Basato sulla lettura diretta del codice (`pilot/*.py`, `run_daily_pilot.bat`),
non su supposizioni. Ogni riga sotto è verificata in codice o misurata su disco.

## Catena di esecuzione reale

```
Task Scheduler (trigger 06:00 + catch-up 12:00, idempotente su data/raw/<oggi>.jsonl)
→ run_daily_pilot.bat
→ python -m pilot.run_monitor --target pilot_daily_all
→ pilot/run_all.py: run()
   collect → clean → entities → dedup → score → trending → signals → export_dashboard
→ data/pipeline_health.json scritto SEMPRE (anche su stadio fallito o eccezione)
```

Nota: l'ordine reale include **`entities`** fra `clean` e `dedup` (rigenera
`config/entities.yaml` da `dashboard-config.js`) — il task originale lo omette, probabilmente
per semplicità di stesura, non è un errore da correggere nel codice.

`run_retry.bat`/`rerun_retry.bat`/`serve.bat` esistono ma **non fanno parte di questa pipeline**
(retry delle annotazioni golden-set, server locale) — verificato nei commenti di `run_all.py`.

## Scoperta critica 1 — l'LLM non è nella pipeline giornaliera

`grep` di `from pilot import llm` su tutto `pilot/*.py`: usato solo da `pilot/ask.py` e
`pilot/spend.py`. **Nessuno degli 8 stadi di `run_all.py` chiama `pilot/llm.py`.** `score.py` è
regole/euristiche, non LLM. `ask.py` (query interattiva stile RAG) e `pilot/index.py`/`corpus.db`
sono un sottosistema separato, esplicitamente fuori scope per la FASE 2 ("Niente RAG/vector DB in
questa fase" — il task lo esclude già, questo lo conferma anche dal lato codice).

Conseguenza diretta sul punto 13 del task ("Esegui le chiamate Anthropic/DeepSeek esattamente come
previsto dalla pipeline"): **non c'è nulla da eseguire lì**, la corsa giornaliera reale non spende
token LLM. I secrets `ANTHROPIC_API_KEY`/`DEEPSEEK_API_KEY` restano necessari solo se in futuro si
vuole eseguire `ask.py` o `spend.py` su GitHub — non per `run_all.py`.

## Scoperta critica 2 — `corpus.db` non è lo stato della pipeline

`corpus.db` (2.1 MB) è usato solo da `pilot/ask.py` e `pilot/index.py` — il sottosistema RAG fuori
scope. **Non è letto né scritto da nessuno degli 8 stadi della pipeline giornaliera.** Il "probabile
esempio, da verificare" del task (`corpus.db`, dedup state, baseline) andava verificato: `corpus.db`
va escluso dalla persistenza FASE 2.

## Cosa determina davvero la memoria fra un run e il successivo

Verificato leggendo `collect.py` riga per riga:

```python
# collect.py ~riga 463: dedup contro TUTTI i raw/*.jsonl (non solo oggi)
existing_ids = set()
for path in RAW_DIR.glob("*.jsonl"):
    for line in ...:
        existing_ids.add(json.loads(line)["raw_id"])
# poi: item scartato se item["raw_id"] in existing_ids
```

`data/raw/*.jsonl` (un file per giorno, mai sovrascritto, solo accodato) è **l'unico** meccanismo
che impedisce a `collect` di raccogliere due volte lo stesso articolo tra un run e l'altro. Tutto il
resto della catena è **rigenerato da zero ad ogni run**, in scrittura (`"w"`, non append):

- `clean.py` riga 150: `open(CLEAN_JSONL, "w", ...)` — legge `data/raw/*.jsonl` (glob completo),
  scarta ciò più vecchio di `STALE_DAYS=30`, riscrive `data/clean.jsonl` intero.
- `dedup.py`, `score.py`, `trending.py`, `signals.py`, `export_dashboard.py`: leggono l'output dello
  stadio precedente e riscrivono il proprio, sempre per intero.

**Conclusione verificata (non supposta)**: lo stato minimo necessario perché il run N+1 continui
correttamente dal run N è **`data/raw/*.jsonl`**. Tutto il resto (`clean.jsonl`, `items.jsonl`,
`clusters.jsonl`, `scored_items.jsonl`, `scored_clusters.jsonl`, `entity_salience.jsonl`,
`trending_entities.jsonl`, `signal_candidates.jsonl`) è deterministicamente ricostruibile da
`data/raw/*.jsonl` + `config/*.yaml`, e infatti viene ricostruito ad ogni run comunque.

`data/errors.jsonl` (append-only, 2.15 MB) alimenta `pipeline_health.json` filtrando per timestamp
del run corrente (`_errors_since`) — utile da persistere per non perdere lo storico errori-per-fonte,
ma non necessario per la correttezza del dedup.

## Problema di dimensioni — misurato, non stimato

```
data/raw/2026-08-27.jsonl    3.2 MB
data/raw/2026-08-28.jsonl    6.1 MB
data/raw/2026-08-29.jsonl   64.7 MB   <- crescita non lineare, da capire perché
data/raw/ totale             71 MB (3 giorni)
```

Con finestra di collezione `BACKFILL_DAYS_DEFAULT = 30` giorni e questo pattern di crescita, uno
snapshot che copre l'intera finestra utile potrebbe arrivare a **diverse centinaia di MB, forse oltre
1 GB**, prima che `STALE_DAYS=30` renda irrilevanti i file più vecchi. Nessun file individuale supera
ancora i 100 MB (limite hard di GitHub per file), ma il singolo giorno 08-29 è già a 65 MB — un
salto di scala che non ho ancora spiegato (non ho scavato nella causa, serve capire se è un pattern
normale o un'anomalia di quel run specifico prima di dimensionare la persistenza).

`data/clean.jsonl` (138 MB, il file grande già segnalato nell'audit Pages FASE 1) **non ha bisogno
di essere persistito**: è rigenerato ad ogni run da `data/raw/`, quindi trascinarlo tra i run
sarebbe uno spreco di banda e la violazione esplicita della regola "non trascinare tutti i 257 MB"
del task.

`data/golden/`, `data/golden_b3/`, `data/fixtures/`, `data/baseline_20260827/` (884 KB + 1.3 MB +
476 KB + 8.9 MB): dataset di calibrazione/test usati da `pilot/test_pipeline.py` e dai task BETA
precedenti, non toccati da `run_all.py` — **non fanno parte dello stato della pipeline**, restano
solo nel repo di codice (già versionati lì, verificare se voluto).

## Classificazione file (come richiesto dal task)

| File/percorso | Classe | Note |
|---|---|---|
| `pilot/*.py`, `run_daily_pilot.bat`, `requirements.txt`, `config/*.yaml` | CODE | Versionati nel repo pubblico del codice |
| `data/raw/*.jsonl` | **PERSISTENT_STATE** | Unico stato che serve davvero fra un run e l'altro — vedi sopra |
| `data/errors.jsonl` | PERSISTENT_STATE (opzionale) | Storico errori per fonte, append-only; utile ma non critico per la correttezza |
| `data/pipeline_health.json` | DASHBOARD_OUTPUT | Pubblicato su Pages, 593 B, già gestito in FASE 1 |
| `assets/data/rassegna.json`, `trending.json`, `signals.json` | DASHBOARD_OUTPUT | Rigenerati ad ogni run da `export_dashboard.py`/`trending.py`/`signals.py`, pubblicati su Pages |
| `data/clean.jsonl`, `items.jsonl`, `clusters.jsonl`, `scored_items.jsonl`, `scored_clusters.jsonl`, `entity_salience.jsonl`, `trending_entities.jsonl`, `signal_candidates.jsonl` | TEMPORARY | Rigenerati per intero ad ogni run da `data/raw/` + config; non serve persisterli |
| `data/rassegna_preview.html`, `trending_signals_preview.html` | TEMPORARY | Anteprime di debug locali |
| `data/scheduler_run.log` | LOCAL_ONLY | Log del Task Scheduler Windows, non applicabile su GitHub Actions (che ha i suoi log) |
| `data/corpus.db`, `pilot/ask.py`, `pilot/index.py` | LOCAL_ONLY (fuori scope) | Sottosistema RAG, esplicitamente escluso dalla FASE 2 |
| `data/golden/`, `golden_b3/`, `fixtures/`, `baseline_20260827/` | LOCAL_ONLY | Dataset di test/calibrazione, non toccati dalla pipeline runtime |
| `.env` | SECRET | Mai versionato, già in `.gitignore`, verificato con `git check-ignore -v` in FASE 1 |
| `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY` | SECRET | Nomi confermati in `.env`/`.env.example`; **non usati dalla pipeline giornaliera** (vedi Scoperta critica 1) |

## Portabilità Windows → Linux — prima occhiata

Non ancora corretto nulla (punto 2 del task, da fare dopo aver chiuso la persistenza). Osservazioni
preliminari dalla lettura:

- `run_daily_pilot.bat` è specifico Windows (Task Scheduler, path assoluto Windows all'eseguibile
  Python) — su GitHub Actions non si usa affatto, si chiama direttamente
  `python -m pilot.run_monitor --target pilot_daily_all` (o `run_all.py`) dal workflow YAML.
- `pilot/*.py` usa `pathlib.Path` ovunque visto finora (`ROOT = Path(__file__).resolve().parent.parent`)
  — niente path Windows hardcoded trovato nei file letti.
- Da verificare ancora: encoding esplicito nelle `open()` (finora sempre `encoding="utf-8"`,
  buon segno), timezone (`datetime.now(timezone.utc)` usato correttamente in `run_all.py`), eventuali
  subprocess/comandi shell Windows-specifici in `collect.py`/`entities.py` non ancora ispezionati riga
  per riga.

## Prossimi passi (non ancora fatti)

Fermato qui per decidere con l'utente la strategia di persistenza prima di scrivere qualunque
workflow — vedi messaggio di chat. Ancora da fare quando la persistenza è chiara: portabilità
completa, dipendenze, secrets su GitHub, workflow, validation gate, deploy, test dei 2 run, scheduler.
