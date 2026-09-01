# TASK — CHIUSURA FASE 4 (task unico, esecuzione autonoma)

**Repo:** `C:\Users\frontofficedx\Desktop\media-pilot` — branch `master`
**Scritto:** 2026-09-01 — sostituisce le domande aperte in `docs/TASK_FASE4_NEXT.md`.
**Le decisioni sono già prese** (§DECISIONI). Non ri-chiedere all'utente: esegui.

## AUTORIZZAZIONI (valide per tutto questo task)

- Modificare il codice, committare, `git push origin master` — **autorizzato**.
- Lanciare `gh workflow run daily-pipeline.yml` — **autorizzato**.
- Riattivare il cron in `.github/workflows/daily-pipeline.yml` — **autorizzato**, allo STEP 5.
- Abilitare nuove fonti in `config/sources.yaml` — **autorizzato**, allo STEP 4.
- Bug, crash, fallback, scelte di debug: **decidi da solo**, non fermarti a chiedere.

**Override esplicito dell'utente, 2026-09-01:** `docs/TASK_FASE3_NEXT.md` e `docs/TASK_FASE4_NEXT.md` §3
vietano di ricalibrare `salience` senza un dataset di etichette *signal-worthiness*, e impongono di
chiedere all'utente. **Quel vincolo è revocato.** L'utente non creerà il dataset. Applica la
correzione strutturale dello STEP 3 e documentala come *split distribuzionale*, non come
calibrazione. Non fermarti su quella riga.

## BUDGET (vincolo duro)

- **Massimo 3 run Actions** per lo STEP 2 (TASK F). Ogni run costa 20-40 minuti reali.
- Se dopo il terzo run `duration_sec` è ancora > 1200s: **fermati**, scrivi i numeri in
  `docs/TASK_FASE3_NEXT_RESULTS.md`, salta allo STEP 3 e riporta. Non continuare a tarare.
- Massimo 1 run per lo STEP 4. Totale run in tutto il task: ≤ 5.

## DECISIONI GIÀ PRESE (non rimetterle in discussione)

| Domanda aperta in FASE 4 | Decisione |
|---|---|
| Target `duration_sec` | **< 1200s** (non 600s). 600s era arbitrario su 33 fonti in rete. |
| Target `window_actual_days` | **≥ 15/25 fonti a ≥7 giorni** (non 20/25). |
| Concorrenza (`BACKFILL_FETCH_WORKERS=8`) | **Torna a 1.** Il sequenziale è l'unica config con `items_written` noto-buono (1055). Non tarare una variabile non spiegata: eliminala. |
| Golden dataset per `salience` | **Non si fa.** Correzione strutturale, vedi STEP 3. |
| Ordine H (cron) vs I (fonti) | **Prima le fonti, poi il cron.** Non si accende l'automazione su un carico che stai per cambiare. |

---

## STEP 0 — Verifica di partenza

```bash
cd "C:\Users\frontofficedx\Desktop\media-pilot"
git checkout master
git pull --rebase origin master
git log --oneline -3
git status
python -m pilot.test_pipeline
```

Atteso: `c5e0a4f` (o successivo) in testa, working tree pulito (a parte i doc), 27/27 test.

**Mai `git clean -fdx` in questo repo.** Se `data/raw/` manca:

```bash
git fetch origin runtime-state
git show origin/runtime-state:data/raw/2026-08-30.jsonl > data/raw/2026-08-30.jsonl
git show origin/runtime-state:data/raw/2026-08-31.jsonl > data/raw/2026-08-31.jsonl
```

**Prima di ogni push: `git pull --rebase origin master`** — il workflow scrive su `master` da solo.

---

## STEP 1 — La causa vera di `duration_sec`: il gate del backfill non scatta mai

Due sessioni hanno attribuito il tempo alla concorrenza e alla dimensione del corpus. **È il gate.**

`pilot/collect.py:493` chiama `_needs_history_supplement(source, days)` dove `days` arriva da
`collect(days=BACKFILL_DAYS_DEFAULT)` = **30**. Il gate (`collect.py:449`) salta il backfill solo se
`window_actual_days >= days`. Nessuna fonte è vicina a 30 giorni (la migliore è a ~9), quindi
**tutte e 25 le fonti RSS rifanno fino a 100 fetch di backfill a ogni run, per sempre.**
Il criterio di successo del progetto è 7 giorni, non 30.

### Modifiche da fare (tutte in un commit)

1. **`pilot/collect.py`** — nuova costante accanto a `BACKFILL_DAYS_DEFAULT`:
   ```python
   BACKFILL_TARGET_DAYS = 7  # finestra che consideriamo "abbastanza": oltre questa il supplemento si spegne
   ```
   e alla riga del gate in `collect()` passa **la nuova costante, non `days`**:
   ```python
   if is_rss and supplement_history and _needs_history_supplement(source, BACKFILL_TARGET_DAYS):
   ```
   **Non abbassare `BACKFILL_DAYS_DEFAULT`**: quel valore alimenta anche `window_start`
   (`collect.py:479`), che filtra `collect_from_rss` / `collect_from_html_source`. Cambiarlo
   restringerebbe di nascosto tutta la raccolta. I test a `test_pipeline.py:455-456` chiamano già
   `_needs_history_supplement` con `days=7`: non si rompe nulla.

2. **`pilot/collect.py:23`** — `MAX_BACKFILL_URLS = 100` → **`50`**.
   Insieme al gate: da 25 fonti × 100 fetch a ~16 × 50. Le due modifiche spingono nella stessa
   direzione, quindi un risultato buono resta interpretabile anche se sono impilate.

3. **`pilot/collect.py:29`** — `BACKFILL_FETCH_WORKERS = 8` → **`1`**.
   `ThreadPoolExecutor(max_workers=1)` è valido: nessun codice da cancellare, la concorrenza
   sparisce come variabile. Aggiorna il commento sopra spiegando che il run `9d4f2a1` a 8 worker ha
   fatto crollare `items_written` 1055 → 340 e che la causa non è stata isolata.

4. **`pilot/util.py:43`** — `fetch()` **ha già** retry con backoff su 429 e cattura già
   `URLError`/`TimeoutError`/`ConnectionError`. Non riscriverlo. Serve solo allargare la lista di
   codici:
   ```python
   if e.code in (429, 502, 503, 504) and attempt < retries:
   ```
   e includere quei codici nel ramo `kind = "RATE_LIMIT"` se ha senso, altrimenti lasciali
   `FETCH_ERROR`.

5. `python -m pilot.test_pipeline` → deve restare verde. Commit:
   `fix: gate backfill on 7-day target, halve URL cap, drop concurrency`

---

## STEP 2 — Run di verifica (max 3)

```bash
git pull --rebase origin master && git push origin master
gh workflow run daily-pipeline.yml
```

Attendi il completamento (20-40 min), poi:

```bash
gh run list --workflow=daily-pipeline.yml --limit 1 --json databaseId,conclusion,createdAt
git fetch origin master
git show origin/master:data/pipeline_health.json
```

Leggi `duration_sec`, `items_fetched`, `items_written`, `sources_failed`. Confronta con i tre run
già registrati in `docs/TASK_FASE3_NEXT_RESULTS.md`.

**Criterio di successo:** `duration_sec < 1200` **e** `items_written ≥ 800`.

- Successo → STEP 3.
- `duration_sec` ancora alto ma `items_written` sano → run 2 con `MAX_BACKFILL_URLS = 30`.
- `items_written` crollato di nuovo (< 500) anche a 1 worker → la concorrenza non c'entrava:
  guarda `gh run view <id> --log` e `data/errors.jsonl`, individua quali fonti falliscono e perché,
  correggi la causa vera, run 3.
- Esaurito il budget di 3 run senza successo → scrivi i numeri, riporta, **vai allo STEP 3
  comunque** (F non blocca G).

Aggiorna `docs/TASK_FASE3_NEXT_RESULTS.md` con i numeri prima/dopo a ogni run. Commit per run.

---

## STEP 3 — `salience`: correzione strutturale (nessun run Actions, tutto in locale)

Problema (misurato: 28/28 candidati `true`, mai `false`):

- `pilot/signals.py:91` — `or sal["any_primary"]` rende vero quasi tutto: `is_primary_in_event`
  (`entity_salience.py:75`) è `centrality >= max_centrality_in_cluster`, quindi l'entità più
  centrale di un cluster è **sempre** primary in quel cluster.
- La formula (`entity_salience.py:76-80`) ha tetto **1.65** e 15 dei 28 valori reali sono
  esattamente al tetto.

### Fai questo

1. Togli `or sal["any_primary"]` da `signals.py:91`. Lascia `is_primary_in_event` nei dati
   (`entity_salience.py` continua a scriverlo): esce dal **gate**, non dal dataset.
2. Rigenera in locale, senza rete:
   ```bash
   python -m pilot.run_all --no-collect
   ```
   e conta su **tutto** `data/signal_candidates.jsonl` (MONITORING + REVIEW, non solo i REVIEW
   esportati) quanti hanno `salience: true` / `false`, e come si sposta `classification`.
3. Se `salience` è ancora `true` su ≥ 90% dei candidati, alza `SALIENCE_SIGNAL_MIN` alla **mediana
   osservata** di `max_salience`. Con 15/28 al tetto la mediana sarà 1.65 e lo split diventa
   "al tetto vs sotto": **è un discriminatore reale, ma scrivilo per quello che è** — una divisione
   distribuzionale, non una soglia calibrata. Non ridisegnare la formula: senza etichette non hai
   modo di sapere se un range più largo sarebbe *migliore*, solo *diverso*.
4. `python -m pilot.test_pipeline`. **Aspettati che
   `test_16_signal_candidate_review_needs_multiple_real_signals` si rompa.** Leggi il test prima di
   toccarlo: se asserisce un conteggio o usa una fixture costruita quando `salience` era sempre
   vero, **aggiorna la fixture, non la logica**. Se invece asserisce un invariante di dominio
   ancora valido, è il tuo cambiamento a essere sbagliato: rivedilo.
5. Commit: `fix: drop any_primary override from salience gate, split on observed distribution`
   Documenta in `docs/TASK_FASE3_NEXT_RESULTS.md`: distribuzione prima/dopo, quanti candidati
   cambiano `classification`, e la frase esplicita che non è una calibrazione su golden data.

---

## STEP 4 — Nuove fonti (13 candidate)

Solo **dopo** che lo STEP 2 è chiuso: non mescolare modifiche a `collect.py` con l'aggiunta di fonti.

Task già scritto: `C:\Users\frontofficedx\Desktop\media-pilot-RECUPERO-2026-08-31\TASK_SOURCE_EXPANSION_02.md`.
Elenco: le 13 `READY_NOT_ENABLED_YET` in `docs/SOURCE_EXPANSION_AUDIT_01.csv`.

1. **Riverifica la raggiungibilità di ognuna prima di abilitarla** — l'audit è del 29/08 e almeno
   una fonte risultava già morta allora. Uno script usa-e-getta con `pilot.util.fetch` va benissimo;
   non serve committarlo.
2. Abilita in `config/sources.yaml` solo quelle che rispondono. Scarta le altre e annota perché.
3. `python -m pilot.test_pipeline`, commit `feat: enable N verified sources from expansion audit`,
   push, **un** run Actions.
4. Controlla che `duration_sec` regga: le nuove fonti partono da `window_actual_days: null` → 0,
   quindi fanno backfill. Se `duration_sec` supera 1500s, abbassa `MAX_BACKFILL_URLS` invece di
   togliere fonti (il gate le spegnerà da solo appena raggiungono 7 giorni).

**Fuori scopo, invariato:** niente scraper Facebook/Instagram, niente Scrapling/Playwright, non
rifare l'audit runtime né quello delle fonti.

---

## STEP 5 — Riaccendere il cron

Solo se lo STEP 2 (o lo STEP 4) ha chiuso con `duration_sec < 1200`.

In `.github/workflows/daily-pipeline.yml`, decommenta le righe 5-12 lasciando **una sola**
schedulazione, non due:

```yaml
  schedule:
    - cron: '0 5 * * *'
```

Sostituisci il commento sopra (che spiega perché era stato disattivato il 31/08) con una riga che
dice perché è riacceso: gate del backfill a 7 giorni + cap a 50 → il costo per run cala man mano
che le fonti convergono.

Commit `chore: re-enable daily schedule after backfill gate fix`, push. Verifica il giorno dopo che
il run automatico sia partito e sia verde.

Con il cron acceso, `window_actual_days` converge da solo: il target ≥15/25 non richiede più run
manuali.

---

## STEP 6 — TASK L: la prima analisi

Un solo deliverable, il più economico che riusa dati già prodotti: **andamento per entità nel
tempo**.

- Sorgente: `assets/data/trending.json` + gli storici in `data/raw/*.jsonl` già presenti.
- Output: una vista nella dashboard esistente (`radar.js` / `data.js` hanno già lo switch
  `mode:'api'` — **alimentali, non riscriverli**, vedi `docs/PROJECT_AUDIT.md`) che mostra per le
  entità di `config/entities.yaml` le menzioni per giorno sulla finestra disponibile.
- **Niente numeri inventati.** `docs/PROJECT_AUDIT.md` avverte che gli item della dashboard sono
  *scenario-shaped* (`risk_score`, `create_case`, `human_review` sono scritti a mano, non esiste un
  campo `url`). Questa vista deve leggere solo campi realmente prodotti dalla pipeline. Se un
  pannello della dashboard non è alimentabile con dati reali, lascialo com'è e dillo nel report.

Le altre tre opzioni (confronto fra testate sullo stesso evento, anomalie per fonte, digest
periodico) restano da fare in un task successivo. Non farle ora.

---

## CONSEGNA

- Un commit per step, messaggi in inglese, `git pull --rebase origin master` prima di ogni push.
- Il registro dei numeri resta `docs/TASK_FASE3_NEXT_RESULTS.md`. Aggiorna quello, non questo file.
- **Un solo report finale**, alla fine di tutto — niente aggiornamenti intermedi. Deve contenere:
  la tabella dei run (commit, `duration_sec`, `items_written`, `sources_failed`,
  `window_actual_days` X/25), cosa è cambiato in `salience` con i numeri prima/dopo, quante fonti
  sono state abilitate e quante scartate, se il cron è acceso, e **cosa resta aperto**.
- Se uno step risulta già fatto da una sessione precedente: dillo e saltalo. Non rifare lavoro
  fatto, non inventare lavoro non richiesto.
