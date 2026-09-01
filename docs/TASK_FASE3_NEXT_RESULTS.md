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
- `salience`: **lasciato invariato**, stesso problema di `cross_entity` ma la correzione è una
  modifica alla formula di `entity_salience.py` (togliere l'`or any_primary`, allargare il range
  oltre il tetto 1.65), non una cancellazione — e serve comunque sapere DOVE tagliare, cosa che
  senza un'etichetta di signal-worthiness non si può stabilire senza indovinare.
- `cross_entity`: **rimosso** (commit `666832a`). Coerente con la via di uscita che il task
  stesso prevede al punto 3: soglia non applicabile, nessun valore nell'intervallo osservato
  (6–22) avrebbe mai potuto far scattare `false`. Prima di applicare la rimozione ho simulato
  l'effetto sui 28 candidati reali: `confidence` ricalcolata su 4 componenti invece di 5 non
  cambia `classification` per **0/28** — non è un componente che stava proteggendo o gonfiando
  artificialmente la lista REVIEW attuale, stava solo aggiungendo +0.2 costante a ogni punteggio
  senza mai discriminare nulla. Nessun consumer frontend/dashboard legge
  `confidence_components.cross_entity` (verificato). 27/27 test verdi.

### Non fatto in questa sessione

- `docs/SIGNAL_CALIBRATION.md` — non scritto: avrebbe dovuto contenere soglie numeriche calibrate
  su golden, che non esistono. Scriverlo con numeri indovinati avrebbe prodotto un documento che
  una sessione futura avrebbe citato come "calibrato" quando non lo è.
- Modifica della formula di `entity_salience.py` per `salience` — decisione in sospeso, non
  implementata (serve sapere dove tagliare, non solo che va tagliato).
- Creazione di un dataset di etichette signal-worthiness — proposta, non fatta (è lavoro
  dell'utente/analista, non sintetizzabile).

### Criterio di accettazione del task originale — verdetto aggiornato dopo `666832a`

- "almeno 3 componenti su 5 cambiano stato in ≥1 entità" → **soddisfatto** (momentum/sources/
  events, mai saturi sui dati freschi) — ma il layer segnali ha ora solo 4 componenti, non 5, per
  la rimozione di `cross_entity`.
- "`classification` produce ≥2 valori distinti" → **soddisfatto** (REVIEW/MONITORING, 22/6 sui
  dati freschi), confermato anche dopo la rimozione (0/28 classificazioni cambiate).

---

## TASK_FASE4_CHIUSURA STEP 1/2 — gate del backfill era la causa vera

Diagnosi confermata leggendo il codice: `collect.py:494` (numerazione pre-fix) passava `days`
(30, da `BACKFILL_DAYS_DEFAULT`) a `_needs_history_supplement`, non i 7 giorni che sono il vero
criterio di successo del progetto. Nessuna fonte era vicina a 30, quindi il gate non scattava mai.
Fix (commit `d988fe5` + `0ce7d84`): nuova costante `BACKFILL_TARGET_DAYS = 7` usata solo nel gate
(non in `window_start`, che resta su `BACKFILL_DAYS_DEFAULT`/`days` per non restringere la
raccolta), `MAX_BACKFILL_URLS` 100→50, `BACKFILL_FETCH_WORKERS` 8→1 (elimina la concorrenza come
variabile non spiegata, vedi run `9d4f2a1` sopra), retry su 502/503/504 oltre a 429 in
`pilot/util.py:fetch()` (label lasciata `FETCH_ERROR`, non `RATE_LIMIT`, per non confondere quella
metrica con l'esistente).

**Nota sul criterio di successo:** la richiesta originale STEP 2 (`items_written ≥ 800`) è stata
corretta a runtime dall'utente — sbagliata per costruzione, perché gate+cap riducono gli item
*nuovi* per definizione (le fonti che saltano il supplemento scrivono zero item di backfill, non
800). Criteri sostitutivi usati da qui in avanti: `duration_sec < 1200`, `sources_failed ≤ 15`,
`items_fetched` in calo netto rispetto al baseline 1250 (run `9d4f2a1`), conteggio fonti con
`window_actual_days ≥ 7` in salita rispetto al baseline 10/33.

### Run 1 — commit `0ce7d84`, run Actions `33458654978`

| metrica | valore | criterio | esito |
|---|---|---|---|
| `duration_sec` | 1939.6 | < 1200 | **FAIL** (+62%) |
| `sources_failed` | 13 | ≤ 15 | OK |
| `items_fetched` | 921 | calo netto da 1250 | OK (−26%) |
| `items_written` | 205 | — (criterio ritirato) | — |
| fonti `window_actual_days ≥ 7` | 11/33 | in salita da 10 | OK (marginale) |

`duration_sec` ancora ben sopra target ma nessun segnale di rottura (fonti fallite in linea,
fetch in calo, finestra che converge) → ramo "ancora alto ma sano" del task: run 2 con
`MAX_BACKFILL_URLS = 30` invece di fermarsi o investigare un crash che non c'è.

### Run 2 — commit `f5c366f`, run Actions `33460839212`

| metrica | valore | criterio | esito |
|---|---|---|---|
| `duration_sec` | 1709.0 | < 1200 | **FAIL** (+42%) |
| `sources_failed` | 15 | ≤ 15 | OK (al limite) |
| `items_fetched` | 762 | calo netto da 1250 | OK (−39%) |
| `items_written` | 92 | — (criterio ritirato) | — |
| fonti `window_actual_days ≥ 7` | 11/33 | in salita da 10 | OK (invariato da run 1, ma sopra baseline) |

Rendimenti decrescenti: cap 50→30 (−40%) ha tagliato `duration_sec` solo del 12% (1939.6→1709.0).
Il log Actions non espone timestamp per-fonte (stdout consegnato in blocco a fine step), ma il
confronto numerico è comunque leggibile: `items_fetched` è sceso 921→762 (−159, ~8 item/unità di
cap tagliata) mentre `duration_sec` è sceso solo 230s — coerente con la nota di `9d4f2a1`
(`duration_sec ≈ items_fetched × 1.87s/item`): a 762 item quella stima dà ~1425s, il resto
(~284s) è overhead fisso (dedup/cluster/LLM/retry) che il cap non tocca. Il cap non è quindi
l'unica leva, ma resta l'unica disponibile nel perimetro di questo task — proseguo con run 3
(budget 3/3) invece di fermarmi qui, perché il calcolo lascia un margine plausibile (non certo)
di arrivare sotto 1200 con un taglio ulteriore.

### Run 3 (finale, budget 3/3) — commit `e51a693`, run Actions `33462832943`

| metrica | valore | criterio | esito |
|---|---|---|---|
| `duration_sec` | 1682.1 | < 1200 | **FAIL** (+40%) |
| `sources_failed` | 18 | ≤ 15 | **FAIL** (peggiorato da 15) |
| `items_fetched` | 660 | calo netto da 1250 | OK (−47%) |
| `items_written` | 45 | — (criterio ritirato) | — |
| fonti `window_actual_days ≥ 7` | 11/33 | in salita da 10 | OK (invariato da run 1/2) |

Cap 30→15 (−50%) ha tagliato `duration_sec` solo dell'1.6% (1709.0→1682.1) e ha **peggiorato**
`sources_failed` (15→18, +3 fonti in più falliscono — probabile: con meno URL disponibili alcune
fonti sitemap/wayback non trovano più abbastanza pagina utile entro il cap e falliscono su
condizioni che a cap più alto non incontravano). Il cap è arrivato al suo punto di rendimenti
negativi: taglia sempre meno tempo e rompe sempre più fonti. Budget di 3 run esaurito con
`duration_sec` ancora sopra il target in tutti e tre i run.

**Decisione finale sul cap:** `MAX_BACKFILL_URLS` riportato a **30** (il valore misurato migliore
sulle due metriche seguite, non un nuovo tentativo — run 2 batte sia run 1 che run 3 su
`sources_failed`, ed è quasi pari a run 3 su `duration_sec`). Non è "continuare a tarare": è
scegliere il migliore fra i tre valori già misurati, non cercarne uno nuovo.

### Verdetto TASK F — target `duration_sec` < 1200 NON raggiunto

Confermata la diagnosi che il gate era la causa principale del comportamento *peggiore* (avrebbe
rifatto backfill per sempre, su ogni fonte, senza convergenza) — quella parte del fix è corretta e
resta in produzione (`BACKFILL_TARGET_DAYS = 7`, verificato che il conteggio fonti a `≥7gg` sale
nel tempo, 10→11/33 in 3 run). Ma il gate da solo non basta a portare `duration_sec` sotto 1200 in
un singolo giorno: con `window_actual_days` ancora basso per 22/33 fonti, la maggior parte del
tempo viene ancora dal fetch primario (RSS/HTML) e dal backfill che il gate non ha ancora spento.
La leva `MAX_BACKFILL_URLS` ha rendimenti decrescenti già a cap=30 e diventa controproducente a
cap=15. Il resto del tempo (~1400-1700s) è pavimento strutturale: fetch di ~30 fonti (RSS + HTML)
più dedup/cluster/LLM su un corpus di ~3500 articoli puliti — nessuna delle leve in scope per
questo task lo riduce ulteriormente senza toccare concorrenza (esclusa per l'esito noto di
`9d4f2a1`) o il numero di fonti (fuori scope, STEP 4 le aumenta).

**Aperto per una sessione futura:** il gate convergerà da solo col cron acceso (STEP 5) — ogni
run che passa sposta più fonti sopra `≥7gg`, quindi `duration_sec` scenderà nei prossimi giorni
senza altro intervento. Se serve un target *immediato* sotto 1200s, le opzioni fuori scope qui
sono: dividere le fonti su più run schedulati (mattina/sera), o reintrodurre concorrenza con un
numero di worker più basso (2-3) e backoff verificato — non tentato in questa sessione perché
fuori budget e perché il task vieta esplicitamente di rimettere mano alla concorrenza senza aver
isolato la causa del crollo `9d4f2a1`.

---

## TASK_FASE4_CHIUSURA STEP 3 — `salience`: correzione strutturale, nessun run Actions

**Override esplicito dell'utente (2026-09-01, in `TASK_FASE4_CHIUSURA.md`):** il divieto di
ricalibrare `salience` senza golden data (`TASK_FASE3_NEXT.md`/`TASK_FASE4_NEXT.md §3`) è
revocato per questo task. Nessun golden set di signal-worthiness creato: questa è una correzione
**strutturale al gate**, non una calibrazione.

### Dati usati: sincronizzati da `runtime-state`, non lo stato locale stantio

Trappola evitata (segnalata dall'advisor prima di misurare): `data/raw/` locale era rimasto fermo
a 3284 righe (stato pre-sessione), mentre i tre run Actions di STEP 2 avevano scritto fino a 3626
righe su `origin/runtime-state` (branch separato da `master`, dove il workflow salva `data/raw` e
`errors.jsonl`). Misurare la distribuzione sui dati vecchi avrebbe calibrato/valutato una soglia
su un corpus che non corrisponde più a quello reale. Sincronizzati i tre file `data/raw/*.jsonl`
da `origin/runtime-state` (`git show origin/runtime-state:data/raw/<file> > data/raw/<file>`)
prima di rigenerare con `python -m pilot.run_all --no-collect`.

### Fix (commit successivo)

Rimossa `or sal["any_primary"]` da `signals.py:91` (linea originale, ora `pilot/signals.py`).
`is_primary_in_event` resta scritto in `entity_salience.jsonl` (esce dal gate del Signal, non dal
dataset — `entity_salience.py` invariato).

### Numeri: stesso corpus fresco, prima/dopo il fix (27 signal candidates)

| | `salience` true | `salience` false | % true |
|---|---|---|---|
| PRIMA (`or any_primary`) | 27 | 0 | 100.0% |
| DOPO (solo `max_salience >= SALIENCE_SIGNAL_MIN`) | 22 | 5 | **81.5%** |

5/27 candidati passano da `salience=true` a `false` grazie alla rimozione dell'`or`. Effetto su
`classification` (ricalcolata sullo stesso corpus, stessi altri 3 componenti invariati):

| | REVIEW | MONITORING |
|---|---|---|
| PRIMA | 21 | 6 |
| DOPO | 20 | 7 |

1 candidato passa da REVIEW a MONITORING (confidence scesa sotto 0.6 per la perdita del
componente salience).

### `SALIENCE_SIGNAL_MIN` NON alzato — criterio del task non raggiunto

Il task chiedeva di alzare la soglia alla mediana osservata **solo se** `salience` resta true su
**≥90%** dei candidati dopo la rimozione dell'`or`. Misurato: 81.5% (22/27), sotto la soglia del
90% — il ramo "alza alla mediana" non si applica. La rimozione dell'`or` da sola è già sufficiente
a far discriminare il componente; non serve toccare `SALIENCE_SIGNAL_MIN` (resta `1.0`). Nota per
completezza: la distribuzione di `max_entity_salience` resta ammassata al tetto 1.65 (16/27 valori
esattamente al tetto, mediana 1.65) — il problema di range descritto in TASK G persiste e resta
un limite noto della formula in `entity_salience.py`, ma non blocca più il gate grazie all'`or`
rimosso, quindi non richiede azione in questo task.

### Test

`python -m pilot.test_pipeline` → 27/27 verdi, **nessuna modifica necessaria**: `test_16` usa una
fixture (`dodik`, `max_salience: 1.3`) che supera comunque `SALIENCE_SIGNAL_MIN = 1.0` senza
l'`or any_primary`, quindi l'asserzione `confidence == 1.0` restava valida a soglia invariata.

---

## TASK_FASE4_CHIUSURA STEP 4 — 7 nuove fonti abilitate su 13 candidate

Delle 13 `READY_NOT_ENABLED_YET` in `docs/SOURCE_EXPANSION_AUDIT_01.csv`, 6 usano
`fetch_method_found: html_home_links`: scartate a monte, non per raggiungibilità ma perché
`pilot/collect.py:collect_from_html_source` dispatcha solo su `method` contenente `"sitemap"` o
`"wayback"` — `html_home_links` non è un metodo che il collector sa eseguire, e implementarlo è
un cambio di codice fuori dallo scope di questo task (fonte: nota della stessa audit riga per
riga, confermata leggendo `collect.py:352-361`). Scartate: RS_IJ_016 (Teslić Danas), RS_IJ_029
(TrebinjeLive), RS_IJ_025 (Katera), RS_IJ_031 (Herceg TV), POL_RS_013 (SDA), SRC_004 (Mondo.ba).

Le restanti 7 (metodo `rss` o `sitemap`, compatibili col collector com'è) sono state riverificate
dal vivo (`pilot.util.fetch`, script usa-e-getta non committato) prima di abilitarle — tutte
rispondono HTTP 200 con contenuto valido, nessuna morta:

| source_id | nome | metodo | esito riverifica |
|---|---|---|---|
| BL_IJ3_009 | Banjaluka.com | rss | OK, 10 entry |
| RS_IJ_008 | Prnjavor.info | rss | OK, 10 entry |
| RS_IJ_022 | Zvornik Danas | rss | OK, 18 entry |
| SRC_010 | Istraga.ba | rss | OK, 10 entry |
| RS_IJ_003 | Kozarski vjesnik | rss | OK, 10 entry |
| FBIH_004 | Raport.ba | rss | OK, 10 entry |
| RS_IJ_026 | Palelive | sitemap (`sitemap_index.xml`, non il default `/sitemap.xml`) | OK, 30 item verificati con `collect_from_sitemap_backfill` in locale |

Abilitate tutte e 7 via `python -m pilot.manage add-source ... --target pilot_daily_all` (aggiunge
sia a `config/sources.yaml` che a `config/monitoring.yaml`). Corretti a mano due difetti del CLI
non pensato per questo caso: `source_type` di default è `manual_add` (non classificato come
"local"/"news" da `score.py:_MENU_PREFIX`, finirebbe nel menu sbagliato della dashboard) →
impostato `media_portal` per coerenza con le fonti locali già attive dello stesso tipo;
`website_url` di default combacia con `feed_url` invece dell'homepage → corretto sulle 7. Per
Palelive (unica non-RSS) il CLI non supporta `method: sitemap` con URL non-default: aggiunto a
mano `sitemap_url: "https://www.palelive.com/sitemap_index.xml"` dopo la generazione via CLI.

`config/sources.yaml`: 33 → 40 fonti. `python -m pilot.test_pipeline` → 27/27 verdi.

**Nota per lo STEP successivo:** le 6 fonti `html_home_links` restano `READY_NOT_ENABLED_YET` —
se servono in futuro, serve prima un metodo di raccolta HTML da homepage in `collect.py` (fuori
scope qui, e in tensione con la policy §4 del progetto "niente parser di paginazione su misura per
fonte").
