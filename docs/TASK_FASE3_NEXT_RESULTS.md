# TASK FASE 3 — risultati

**Scritto:** 2026-08-31/09-01, sessione che ha eseguito i task del predecessore
`docs/TASK_FASE3_NEXT.md`.

---

## ORDINE punto 1 — esito del run `33355679965`

Il run non era "ancora in corso", era **fallito**. Il passo "Run pipeline" ha impiegato
**44m43s** (2683s, non i ~7 min osservati a metà corsa), poi "Commit dashboard outputs" ha
fallito con `! [rejected] master -> master (fetch first)`: master si era mosso (commit TASK F)
durante i 45 minuti di run, il push finale non era un fast-forward. L'intero output di quel
run (`rassegna.json`, `signals.json`, `trending.json`, `pipeline_health.json`) è andato perso,
mai pubblicato. `data/raw` ed `errors.jsonl` invece si sono salvati (push separato, riuscito).

**Fix:** `git pull --rebase` prima di entrambi i push in `daily-pipeline.yml` (commit `83a9a3e`).

---

## TASK F — stato: parzialmente completato, criteri di accettazione NON raggiunti

### Cosa era già fatto all'inizio di questa sessione

Commit `8adf6ae` (di una sessione precedente) implementava già la variante A2 descritta nel task:
`exclude_canonical` popolato da `data/raw/*.jsonl` e passato lungo
`collect()` → `collect_supplemental_history()` → `collect_from_sitemap_backfill()` /
`collect_from_wayback_cdx()`. Verificato leggendo il codice: il filtro si applica **prima** del
cap `MAX_BACKFILL_URLS`, quindi riduce davvero il numero di fetch (non solo li ridirige). 27/27
test verdi, incluso `test_19` nuovo per questo filtro.

### Due bug nuovi trovati e corretti in questa sessione

1. **`UnicodeEncodeError` non gestito** (`pilot/util.py`): un URL da sitemap con un carattere
   non-ASCII grezzo (es. `₂`) mandava in crash `http.client.putrequest` (ascii-only), non
   catturato dal blocco `except` esistente (`URLError`/`TimeoutError`/`ConnectionError` — non
   `UnicodeEncodeError`, che è una `ValueError`). Uccideva l'intera pipeline a metà (fonte 22/33)
   invece di essere loggato come errore di una fonte sola. **Fix:** `quote(url, safe=...)` prima
   della request (commit `128713a`).
2. **Fetch sequenziali** (`pilot/collect.py`): nessuna concorrenza da nessuna parte in `collect()`.
   `duration_sec` ≈ `items_fetched × 1.87s/item` — quasi tutto il tempo di run è I/O di rete
   bloccante, un URL alla volta. Provata parallelizzazione con `ThreadPoolExecutor`
   (`BACKFILL_FETCH_WORKERS=8`, stdlib) sui due loop a volume più alto (sitemap e wayback
   backfill, fino a 100 fetch ciascuno). **Risultato misto** — vedi tabella sotto: `duration_sec`
   è sceso ma `items_written` è crollato e i fallimenti fonte sono aumentati, probabile
   rate-limiting/timeout lato fonti sotto carico concorrente. Non ottimizzato oltre
   (`BACKFILL_FETCH_WORKERS` andrebbe abbassato e/o servirebbe backoff sui 429/503) —
   **ceiling noto, non risolto in questa sessione.**

### Numeri: tre run Actions reali, in ordine

| Run | commit | esito | wall-clock step "Run pipeline" | `duration_sec` pubblicato | items_fetched | items_written | sources_failed | skip (window≥7) |
|---|---|---|---|---|---|---|---|---|
| `33355679965` | `923cde1` (A1 soltanto) | fallito al push finale | 2683s (44m43s, da timestamp Actions) | mai pubblicato (push fallito) | — | — | — | — | 6/25 (baseline pre-F) |
| `33439182040` | `83a9a3e` (+A2, no fix unicode) | **crash** a fonte 22/33 | ~1176s (19m36s, da timestamp) | mai pubblicato (crash) | — | — | — | — |
| `33442356029` | `128713a` (+fix unicode) | **successo**, primo run pulito con A2 | 2339s (da timestamp) | 2338.9 | 1250 | 1055 | 15 | 9/25 |
| `33448822718` | `9d4f2a1` (+concorrenza) | successo | 1721s (da timestamp) | 1720.2 | 1155 | **340** | **17** | 9/25 |

### Criteri di accettazione del task originale — verdetto

- `duration_sec` < 600 → **non raggiunto** (migliore risultato: 1720.2s, 2.9× il target)
- fonti che saltano il supplemento ≥ 20/25 → **non raggiunto** (9/25, invariato tra gli ultimi
  due run)
- nessun articolo perso → **non verificato positivamente**: l'ultimo run (con concorrenza) ha
  scritto 340 item contro i 1055 del run precedente, con più fonti fallite. Prima di riusare
  `BACKFILL_FETCH_WORKERS=8` in produzione andrebbe capito se è perdita reale o fonti che quel
  giorno erano più lente/instabili.
- `python -m pilot.test_pipeline` verde con test su `exclude_canonical` → **fatto** (27/27,
  `test_19`)

### Perché il criterio ≥20/25 potrebbe non essere raggiungibile in un solo run

A2 fa avanzare `window_actual_days` di un giorno o poco più per fonte per run (osservato: quasi
tutte le fonti RSS sono salite di 1 tra il run pre-F e il primo run post-A2). Con la finestra a 7
giorni, le fonti più indietro richiedono più run consecutivi per raggiungere la soglia — non è un
difetto del fix, è come A2 è stato progettato (converge nel tempo, non subito). Con il cron ancora
spento (TASK B), questa convergenza avanza solo con run manuali.

### Non ancora deciso

- Se abbassare `BACKFILL_FETCH_WORKERS` (es. a 3-4) o aggiungere retry/backoff sui 429/503 per
  recuperare il calo di `items_written` mantenendo un po' di velocità.
- Se la strada giusta per `duration_sec` < 600 sia continuare a spingere sulla concorrenza, o
  ridurre `MAX_BACKFILL_URLS`, o dividere le fonti su più run schedulati (es. metà fonti al
  mattino, metà alla sera) invece di un unico crawl completo.
- TASK H (riaccensione cron) resta bloccato: nessuno dei tre run ha rispettato il target
  `duration_sec` < 600.

---

## TASK G — bloccato: non eseguibile come scritto, con una scoperta strutturale sotto

### Il blocco: `data/golden/` non contiene l'etichetta che serve

Il §1 del task chiede di "stabilire dove sta la soglia utile per ciascuna metrica usando
`data/golden/`". Letti tutti e tre i file:

- `golden_dataset.json` (30 righe): `cluster_expected`, `entities_expected`, `duplicate_expected`
  — correttezza di clustering/estrazione entità per articolo.
- `annotations_a.jsonl` / `annotations_b.jsonl` (100 righe ciascuno): `is_political`, `entities`,
  `gloss_it`, `confidence` — di nuovo, per articolo.

Nessuno dei tre contiene un'etichetta **per entità, per finestra temporale**, del tipo "questa
entità in questo momento era davvero un segnale da guardare". È esattamente l'etichetta che
servirebbe per calibrare `MOMENTUM_SIGNAL_MIN`/`SOURCES_SIGNAL_MIN`/`EVENTS_SIGNAL_MIN`/
`SALIENCE_SIGNAL_MIN`/`CO_ENTITY_SIGNAL_MIN` — e non esiste. Il task stesso vieta la via
alternativa ("Non ricalibrare a occhio"): scegliere nuovi numeri guardando min/mediana/max di
`signals.json` sarebbe esattamente quello, quindi non l'ho fatto.

**Creare quell'etichetta è una decisione dell'utente, non qualcosa da sintetizzare**: qualcuno
deve marcare, su una o più liste di entità reali già prodotte, quali avrebbe voluto vedere
segnalate. Non l'ho creata io in questa sessione.

### Quello che invece si può stabilire senza etichette: 2 componenti su 5 sono saturi per costruzione

Ho rigenerato in locale l'intera catena da `data/raw/` reale e fresco (i due run Actions di
questa sessione, tirati da `runtime-state`, `--no-collect`: nessuna rete, stessi dati che ha
prodotto la pipeline vera — output verificato identico byte-per-byte a quello su `origin/master`).
28 signal candidates (22 REVIEW, 6 MONITORING), non i 17 della coppia di run citata dal task
(quella era un dataset più piccolo e più vecchio; la diagnosi §G del task va quindi aggiornata,
non solo confermata):

| componente | true | false | fonte della saturazione |
|---|---|---|---|
| `momentum` | 24 | **4** | discrimina già, nessuna azione |
| `events` | 23 | **5** | discrimina già, nessuna azione |
| `sources` | 21 | **7** | discrimina già, nessuna azione |
| `salience` | 28 | **0** | vedi sotto — strutturale |
| `cross_entity` | 28 | **0** | vedi sotto — strutturale |

Sui dati freschi, **3 componenti su 5 già discriminano** (momentum/sources/events, criterio di
accettazione "≥3 componenti cambiano stato" già soddisfatto entro un singolo run — non è la
stessa misura del task, che confrontava due run consecutivi sulla stessa entità, ma con 3
componenti mai saturi la conclusione regge) e `classification` produce già 2 valori
(REVIEW/MONITORING, non "sempre REVIEW" come nel run più vecchio citato dal task). Restano solo
`salience` e `cross_entity` bloccati a "sempre vero", e per entrambi la causa è nel codice, non
nella soglia:

**`salience`** (`signals.py:88`): `sal["max_salience"] >= SALIENCE_SIGNAL_MIN or sal["any_primary"]`.
`is_primary_in_event` (`entity_salience.py:75`) è `centrality >= max_centrality_in_cluster` — per
costruzione, l'entità con centralità massima in un cluster è SEMPRE "primary" in quel cluster.
Per le entità curate che arrivano in `trending` (non stringhe generiche), è quasi sempre vero che
sono l'entità con centralità massima in almeno un cluster a cui partecipano: 5 dei 28 candidati
hanno `max_entity_salience < 1.0` (fino a 0.45) eppure `salience=true` **solo** grazie a questo
`or`. Il resto (23/28) supera comunque 1.0 sul valore numerico — ma la distribuzione è satura
verso l'alto: `entity_salience.py:76-80` limita il valore a `centrality(0.3-1.0) +
ripetizione(0-0.5) + primary_bonus(0/0.15)`, tetto assoluto 1.65, e **15 dei 28 valori misurati
sono esattamente 1.65** (il tetto). Nessuno spostamento di `SALIENCE_SIGNAL_MIN` dentro
l'intervallo osservato (0.45–1.65) può far scendere `salience` sotto ~82% true, perché la
distribuzione stessa è ammassata al tetto — è un problema di range della metrica, non di soglia.

**`cross_entity`** (`CO_ENTITY_SIGNAL_MIN=2`): `max_co_entities_in_event` osservato su questo run
va da **6 a 22** (minimo 6, non 2) — mai sotto la soglia attuale, quindi qualunque soglia ≤6 non
cambierebbe nulla. Causa strutturale: `config/entities.yaml` traccia 55 entità curate (partiti,
leader, istituzioni della politica bosniaca), e un cluster di notizie politiche ne nomina quasi
sempre diverse insieme (un articolo su un voto parlamentare cita partito, leader, istituzione
nello stesso pezzo) — non è un artefatto del run, è come è fatta la copertura politica in
BiH/RS su questo insieme di entità.

### Raccomandazione, non decisione presa

- `momentum`/`sources`/`events`: **nessuna azione**, già calibrati abbastanza da discriminare.
- `salience`: il vincolo strutturale è il tetto a 1.65 e l'`or any_primary` che aggira la soglia
  del tutto per 5/28 casi. Rialzare `SALIENCE_SIGNAL_MIN` da solo non risolve (resterebbe ~82%
  true); andrebbe tolto l'`or any_primary` E allargato il range della metrica stessa (es. non
  saturare la ripetizione a 0.5, o pesare diversamente centralità/primarietà) — è una modifica
  alla formula di `entity_salience.py`, non alla soglia di `signals.py`, e serve comunque
  un'etichetta per sapere DOVE tagliare.
- `cross_entity`: coerente con la via di uscita che il task stesso prevede al punto 3 — **soglia
  non applicabile, il task autorizza la rimozione se resta sempre vero dopo il tentativo di
  taratura**. Qui il tentativo (osservare il range reale) mostra che nessuna soglia nell'intervallo
  osservato può funzionare. Non l'ho rimosso: è una modifica di codice/schema (`signals.py`,
  `assets/data/signals.json`, eventuale UI che legge `confidence_components.cross_entity`) che
  richiede conferma esplicita prima di toccarla.

### Non fatto in questa sessione

- `docs/SIGNAL_CALIBRATION.md` — non scritto: avrebbe dovuto contenere soglie numeriche calibrate
  su golden, che non esistono. Scriverlo con numeri indovinati avrebbe prodotto un documento che
  una sessione futura avrebbe citato come "calibrato" quando non lo è.
- Rimozione di `cross_entity` o modifica di `salience` — decisioni in sospeso, non implementate.
- Creazione di un dataset di etichette signal-worthiness — proposta, non fatta (è lavoro
  dell'utente/analista, non sintetizzabile).
