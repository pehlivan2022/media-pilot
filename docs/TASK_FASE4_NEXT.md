# TASK — FASE 4, cosa manca e come finirlo

**Repo:** `C:\Users\frontofficedx\Desktop\media-pilot` (branch `master`)
**Scritto:** 2026-09-01, da una sessione che ha eseguito `docs/TASK_FASE3_NEXT.md` fino in fondo
(tre run Actions reali, due bug corretti, TASK G in parte risolto) e si è fermata sui punti che
restano qui sotto — bloccati da una decisione, non da lavoro non fatto.
**Log completo con tutti i numeri misurati:** `docs/TASK_FASE3_NEXT_RESULTS.md` (leggilo per il
dettaglio; questo file è il punto di ripartenza, non il registro).

Questo documento è pensato per essere letto da un'altra AI/sessione senza contesto pregresso:
ogni claim ha il file/riga o il commit a supporto, non "si dice".

---

## 0. PRIMA DI TUTTO

```bash
git log --oneline -5   # deve mostrare c5e0a4f in testa (o successivo)
git status              # deve essere pulito
python -m pilot.test_pipeline   # deve dare 27/27 (o più, se nel frattempo sono stati aggiunti test)
```

**Mai `git clean -fdx` in questo repo** — il 31/08 ha cancellato `data/raw/`, `errors.jsonl` e
`.env` in modo irreversibile. `data/raw/` non è tracciato su `master`: vive solo sul branch
`runtime-state`. Per riportarlo in locale:
```bash
git fetch origin runtime-state
git show origin/runtime-state:data/raw/2026-08-30.jsonl > data/raw/2026-08-30.jsonl
git show origin/runtime-state:data/raw/2026-08-31.jsonl > data/raw/2026-08-31.jsonl
```
poi `python -m pilot.run_all --no-collect` per rigenerare `assets/data/*.json` senza rete (utile
per verificare qualunque modifica a `signals.py`/`entity_salience.py`/`score.py` senza aspettare
un run Actions da 30-45 minuti).

**Prima di ogni push**: `git pull --rebase origin master` — il workflow scrive su `master` da solo
a fine run (`daily-pipeline.yml`, fix in `83a9a3e`), quindi un push diretto senza rebase può
essere rifiutato (non-fast-forward) se un run è terminato nel frattempo.

---

## 1. STATO ALLA FINE DI QUESTA SESSIONE

| | |
|---|---|
| Cron | **disattivato** (`daily-pipeline.yml`, righe 5-12 commentate) — nulla parte da solo |
| TASK F (durata pipeline) | codice corretto e funzionante, **obiettivo `duration_sec < 600` NON raggiunto** — vedi §2 |
| TASK G (segnali) | `cross_entity` rimosso (componente costante, autorizzata la rimozione dal task originale), `salience` **non ancora corretto** — vedi §3 |
| TASK H (riaccensione cron) | bloccato da F |
| TASK I (allargare fonti) | non toccato, task separato e indipendente — vedi §4 |
| TASK L (analisi risultati) | sbloccato da G solo in parte — vedi §5 |

Tre run Actions reali in questa sessione, in ordine (dettaglio completo in `TASK_FASE3_NEXT_RESULTS.md`):

| commit | esito | wall-clock | items_written | sources_failed |
|---|---|---|---|---|
| `83a9a3e` | crash (`UnicodeEncodeError` su URL sitemap non-ASCII, corretto in `128713a`) | ~1176s poi crash | — | — |
| `128713a` | **successo**, sequenziale | 2339s (39min) | 1055 | 15 |
| `9d4f2a1` | successo, con `ThreadPoolExecutor` (8 worker) | 1721s (29min) | **340** | **17** |

---

## 2. TASK F — `duration_sec` ancora 2.9× sopra il target, causa nota

### Cosa è già vero e verificato (non ripetere il lavoro)

- La variante A2 (`exclude_canonical` popolato da `data/raw/*.jsonl`, passato lungo
  `collect()` → `collect_supplemental_history()` → `collect_from_sitemap_backfill()`/
  `collect_from_wayback_cdx()`) è implementata e **riduce davvero il numero di fetch** (il filtro
  si applica prima del cap `MAX_BACKFILL_URLS`, verificato leggendo `pilot/collect.py:198-224`).
- Un `UnicodeEncodeError` che uccideva l'intera pipeline su URL non-ASCII è corretto
  (`pilot/util.py`, `fetch()` ora fa `quote(url, safe=...)` prima della request).
- Il push-race su `master`/`runtime-state` è corretto (`git pull --rebase` in
  `.github/workflows/daily-pipeline.yml`, prima di ogni `git push`).
- **La causa di `duration_sec` alto è nota con certezza, non è un'ipotesi**: sul run sequenziale
  (`128713a`), `duration_sec` (2338.9s) ≈ `items_fetched`(1250) × 1.87s/item. Nessuno stadio dopo
  `collect()` fa chiamate di rete (verificato: `score.py`, `dedup.py`, `signals.py` non hanno
  `import requests`/`urlopen`/chiamate LLM). Il tempo è quasi tutto in `collect()`, fetch HTTP
  bloccanti.

### Cosa è stato provato e NON ha funzionato come sperato

`pilot/collect.py:23-29` — `BACKFILL_FETCH_WORKERS = 8`, `ThreadPoolExecutor` sui due loop a
volume più alto (`collect_from_sitemap_backfill`, `collect_from_wayback_cdx`, fino a 100 fetch
ciascuno). Risultato sul run reale (`9d4f2a1`, confrontato con `128713a` a parità di codice A2):

- `duration_sec`: 2338.9 → 1720.2 (**-26%**, non l'8× atteso da 8 worker concorrenti)
- `items_written`: 1055 → **340** (crollo)
- `sources_failed`: 15 → **17**

**Correlazione osservata, causa non confermata**: è plausibile che 8 connessioni concorrenti
verso lo stesso host triggerino rate-limiting/timeout lato fonte che il fetch sequenziale non
incontrava, ma questa sessione non ha isolato la variabile (nessun run di controllo con
`BACKFILL_FETCH_WORKERS` più basso, es. 3-4, per vedere se il calo di `items_written` scompare o
resta). **Non dare per assodato che la concorrenza sia la causa del calo — verificalo prima di
scartarla o di tenerla.**

### Le tre strade non ancora provate, in ordine di costo

1. **Abbassare `BACKFILL_FETCH_WORKERS`** (es. 3-4) e/o aggiungere retry con backoff sui codici
   429/503 in `pilot/util.py:fetch()`. Costo: un run Actions (~20-40 min) per verificare se
   recupera `items_written` mantenendo un po' di velocità. Rischio più basso, non tocca la logica
   di raccolta.
2. **Ridurre `MAX_BACKFILL_URLS`** (`pilot/collect.py:23`, oggi 100) per le fonti che ancora
   necessitano il supplemento. Riduce direttamente il volume, ma rallenta la convergenza di
   `window_actual_days` (già lenta, vedi sotto) e potrebbe non bastare da solo.
3. **Dividere le fonti su più run schedulati** (es. metà mattina, metà sera, o batch rotanti)
   invece di un crawl completo di 33 fonti in un run. Cambia la semantica del cron (§4 di
   `TASK_FASE3_NEXT.md` lo accennava già), richiede più lavoro di design ma è la strada più
   robusta se le prime due non bastano.

### Il secondo problema, indipendente da `duration_sec`: A2 converge troppo lento

`window_actual_days` per le fonti RSS (25 su 33 fonti totali) è salito da 6/25 ≥7gg a 9/25 dopo
il primo run pulito con A2 (`128713a`), **ed è rimasto 9/25** dopo il run con concorrenza
(`9d4f2a1`) — nessun avanzamento nel secondo run, plausibilmente per lo stesso motivo del calo di
`items_written` (fonti fallite non scrivono nuova storia). Il criterio del task originale
(`≥20/25`) richiederebbe molti più run per convergere anche in condizioni ideali: quasi tutte le
fonti sono salite di ~1 giorno per run pulito. **Non è detto che ≥20/25 sia un criterio
raggiungibile in un numero ragionevole di run manuali — vale la pena chiedere all'utente se
tenerlo com'è o abbassarlo (es. ≥15/25) una volta che `duration_sec` è sotto controllo.**

### Come verificare

```bash
gh workflow run daily-pipeline.yml
# poi, dopo il completamento:
gh run list --workflow=daily-pipeline.yml --limit 1 --json databaseId,conclusion
git fetch origin master
git show origin/master:data/pipeline_health.json   # duration_sec, items_fetched, items_written, sources_failed
```
Ogni run reale costa 15-40 minuti reali di attesa — non è simulabile in locale (richiede fetch di
rete verso ~33 fonti). `python -m pilot.run_all --no-collect` in locale (dopo aver ripreso
`data/raw` da `runtime-state`, §0) verifica invece la logica di elaborazione (clean/dedup/score/
trending/signals) senza rete, utile per TASK G ma non per misurare `duration_sec`.

---

## 3. TASK G — `salience` ancora saturo, stessa causa di `cross_entity` ma non rimovibile allo stesso modo

### Cosa è già fatto (non ripetere)

- `cross_entity` rimosso da `pilot/signals.py` (commit `666832a`): `CO_ENTITY_SIGNAL_MIN`
  eliminato, il componente tolto da `components_fired`/`_why_now`. `confidence` ora media su 4
  componenti invece di 5. Simulato sui 28 candidati reali prima di applicarlo: 0/28
  classificazioni cambiate — rimozione sicura, non ha alterato cosa arriva in REVIEW oggi.
- Verificato che `momentum`/`sources`/`events` **discriminano già** sui dati reali attuali (24/28,
  21/28, 23/28 true su 28 candidati) — diagnosi del task originale basata su un dataset più
  vecchio e più piccolo, non più valida. **Nessuna azione richiesta su questi tre.**

### Il problema rimasto: `salience`

`pilot/signals.py:91`: `"salience": sal["max_salience"] >= SALIENCE_SIGNAL_MIN or sal["any_primary"]`

Sui 28 candidati reali (rigenerati da `data/raw` fresco, `--no-collect`, output verificato
identico a quello pubblicato da Actions): **28/28 true**, mai false. Due cause, entrambe nel
codice, non nella soglia `SALIENCE_SIGNAL_MIN = 1.0`:

1. **`or sal["any_primary"]`** — `pilot/entity_salience.py:75`:
   `is_primary_in_event = h["centrality"] >= max_centrality_in_cluster`. Per costruzione, l'entità
   con centralità massima in un cluster è sempre "primary" in quel cluster. Per le 55 entità
   curate in `config/entities.yaml` (non stringhe generiche), è quasi sempre vero che sono
   l'entità con centralità massima in almeno un cluster a cui partecipano. 5 dei 28 candidati
   misurati hanno `max_entity_salience < 1.0` (fino a 0.45) eppure passano solo grazie a questo
   `or`.
2. **Tetto della formula** — `pilot/entity_salience.py:76-80`:
   `salience = centrality(0.3-1.0) + 0.1*min(max(occ-1,0),5)(0-0.5) + (0.15 if primary else 0)`,
   tetto assoluto **1.65**. 15 dei 28 valori misurati sono esattamente 1.65 (il tetto). Anche
   togliendo l'`or any_primary`, alzare `SALIENCE_SIGNAL_MIN` da solo non risolve granché: la
   distribuzione è ammassata verso l'alto, non è un problema di soglia ma di range della metrica.

### Perché non è stato corretto in questa sessione

A differenza di `cross_entity` (soglia mai raggiungibile in nessun punto dell'intervallo
osservato → rimozione autorizzata esplicitamente dal task originale), qui la scelta non è
binaria: si può (a) togliere l'`or any_primary`, (b) ridisegnare la formula per allargare il
range (es. non saturare la ripetizione a 0.5, pesare diversamente centralità/primarietà), o (c)
lasciare `salience` così ma spostare `SALIENCE_SIGNAL_MIN` più in alto (es. 1.5-1.65) sapendo che
resta comunque ~50%+ true. **Nessuna di queste è "la soglia giusta" senza sapere quali entità
DOVREBBERO essere segnalate — che è esattamente il dato che manca (§3.1 sotto).**

### Il blocco di fondo, vale per qualunque ricalibrazione futura in questo layer

`data/golden/` (`golden_dataset.json`, 30 righe; `annotations_a/b.jsonl`, 100 righe ciascuno) **non
contiene un'etichetta per entità/finestra temporale del tipo "questa era davvero un segnale da
guardare"**. Contiene solo correttezza di clustering/estrazione entità per articolo
(`cluster_expected`, `entities_expected`) e annotazioni di contenuto (`is_political`, `gloss_it`).
Verificato leggendo tutti e tre i file per intero, non per campione.

**Per calibrare `salience` (o qualunque altra soglia di `signals.py`) con dati reali invece che a
occhio, serve creare quel dataset di etichette**: qualcuno (utente/analista) deve guardare una o
più liste di entità/trending reali già prodotte (`assets/data/trending.json`,
`data/signal_candidates.jsonl`) e marcare quali avrebbe voluto vedere segnalate. Questo è lavoro
umano, non sintetizzabile da un'AI senza criterio esterno — **chiedilo esplicitamente all'utente
prima di inventare soglie**, il task originale (`TASK_FASE3_NEXT.md`) vietava esplicitamente la
ricalibrazione a occhio e quel vincolo vale ancora.

### Come verificare qualunque modifica a `entity_salience.py`/`signals.py`

```bash
# dopo §0 (ripreso data/raw da runtime-state):
python -m pilot.run_all --no-collect
python -m pilot.test_pipeline   # in particolare test_16_signal_candidate_review_needs_multiple_real_signals
```
poi ispezionare `data/signal_candidates.jsonl` (tutti i MONITORING+REVIEW, non solo i 22 REVIEW
esportati in `assets/data/signals.json`) per contare quanti componenti cambiano stato prima di
pubblicare qualunque numero come "calibrato".

---

## 4. TASK I — invariato, indipendente da F/G

Task separato, già scritto: `C:\Users\frontofficedx\Desktop\media-pilot-RECUPERO-2026-08-31\TASK_SOURCE_EXPANSION_02.md`.
13 fonti `READY_NOT_ENABLED_YET` in `docs/SOURCE_EXPANSION_AUDIT_01.csv`, da riverificare prima di
abilitarle (l'audit era del 29/08, almeno una fonte risultava già irraggiungibile allora — verifica
di nuovo, più tempo è passato). **Non eseguirlo insieme a modifiche di `collect.py`** (TASK F):
aggiungere fonti mentre si cambia la logica di raccolta rende impossibile capire quale dei due ha
causato una variazione nei tempi o negli item — stesso principio già valido nella sessione
precedente.

---

## 5. TASK L — parzialmente sbloccato, non ancora da iniziare

Il task originale bloccava L su G perché "un layer che classifica tutto REVIEW produce
un'analisi che dice sempre la stessa cosa". Questo non è più vero (`classification` produce già
REVIEW/MONITORING su dati reali, 22/6 su 28), ma **`salience` satura ancora significa che una
frazione dei componenti che alimentano `confidence` non discrimina** — un'analisi costruita sopra
erediterebbe comunque un po' di quella cecità, meno grave di prima ma non zero. Raccomandazione:
chiudere almeno la decisione su `salience` (§3) prima di iniziare L, non necessariamente
implementarla — anche solo decidere "lasciamola così per ora, sappiamo perché" è sufficiente per
sbloccare L con gli occhi aperti.

Quando si inizia L, la domanda da porre all'utente resta quella del task originale — opzioni
concrete, non da decidere da soli: andamento per entità nel tempo, confronto fra testate sullo
stesso evento, anomalie per fonte, digest periodico.

---

## FUORI SCOPO (invariato da `TASK_FASE3_NEXT.md`)

- Niente scraper Facebook/Instagram (via legittima: Meta Content Library, richiesta separata).
- Niente Scrapling/Playwright senza il numero misurato di articoli/settimana che porterebbero le
  fonti `JS_ONLY`/`403` (valutazione in TASK_SOURCE_EXPANSION_02).
- Non rifare l'audit runtime né l'audit fonti: `docs/GITHUB_PIPELINE_RUNTIME_AUDIT.md` e
  `docs/SOURCE_EXPANSION_AUDIT_01.csv` restano validi.

---

## ORDINE CONSIGLIATO

1. **TASK F**: isolare se il calo di `items_written` con concorrenza è causato da
   `BACKFILL_FETCH_WORKERS=8` (run di controllo a 3-4) prima di decidere se tenerla, abbassarla o
   toglierla. Poi valutare `MAX_BACKFILL_URLS` più basso o split multi-run se serve ancora.
2. **TASK G**: portare a decisione (non necessariamente a codice) cosa fare di `salience` —
   serve prima chiedere all'utente se vuole investire nella creazione di un dataset di etichette
   signal-worthiness, o accettare una soluzione strutturale (togliere `or any_primary`,
   ridisegnare la formula) senza calibrazione fine.
3. **TASK H**: riaccendere il cron solo dopo che un run rispetta `duration_sec < 600` (o dopo che
   l'utente accetta esplicitamente un target diverso).
4. **TASK I**: le 13 fonti pronte, separatamente da F, quando F è stabile.
5. **TASK L**: dopo la decisione su `salience` in G (non necessariamente dopo l'implementazione).

## CONSEGNA

- Un commit per task/decisione, messaggi in inglese, sempre `git pull --rebase origin master`
  prima del push (§0).
- Aggiornare `docs/TASK_FASE3_NEXT_RESULTS.md` (non questo file) con i numeri prima/dopo di
  qualunque nuovo run o modifica — questo file (`TASK_FASE4_NEXT.md`) è il punto di ripartenza,
  il registro dei risultati resta quello.
- Se un punto risulta già deciso/fatto da una sessione successiva a questa, dirlo e saltarlo — non
  rifare lavoro già fatto, non inventare lavoro nuovo non richiesto.
