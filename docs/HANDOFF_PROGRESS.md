# HANDOFF — dove siamo, cosa fare se la sessione si interrompe

**Aggiornato 2026-08-29 (giro più recente)**: `TASK_WINDOWS_SCHEDULER_01` FATTO — vedi
`docs/TASK_WINDOWS_SCHEDULER_01_RESULTS.md`. Task Windows `MediaPilot_DailyAll` registrato:
giornaliero alle 06:00, gira solo se l'utente `frontofficedx` è loggato (nessuna password
salvata), esegue `run_daily_pilot.bat` → `python -m pilot.run_monitor --target pilot_daily_all`,
log in `data\scheduler_run.log`. Verificare domattina dopo le 06:00 che il primo run automatico
sia andato a buon fine (`Get-ScheduledTaskInfo -TaskName "MediaPilot_DailyAll"` +
`data\scheduler_run.log`).

**Aggiornato 2026-08-29 (giro precedente)**: `TASK_SOURCE_EXPANSION_DAILY_PILOT_01` FATTO — vedi
`docs/TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md`. Fonti 18 → 33 (15 nuove promosse da un
audit v14 su 51 candidati testati dal vivo). `config/monitoring.yaml` ha un nuovo target
`pilot_daily_all` (1×/giorno, tutte le fonti) — comando:
`python -m pilot.run_monitor --target pilot_daily_all`. Non ripartire da questo task, e' chiuso.

**Aggiornato 2026-08-29 (giro precedente)**: `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02` FATTO —
vedi `docs/TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md` e
`docs/DASHBOARD_REAL_DATA_AUDIT.md`. Nessun nuovo provider esterno (REJECT su 6 candidati). Dashboard
operativa confermata senza simulazioni; pagine demo separate dal menu. Non ripartire da questo task,
e' chiuso.

**Aggiornato: 2026-08-29 — il progetto e' CHIUSO fino a `MEDIA_PILOT_FINAL_HANDOFF.md`.** Stato
reale, istruzioni operative, limiti noti e cosa resta manuale: `docs/FINAL_PROJECT_STATUS.md`.
Non ripartire da questo file per capire lo stato attuale — e' storia (TASK_FIX_00/01, TASK_BETA_01,
TASK_BETA_02, TASK_BETA_03, tutti FATTI, dettagli nei rispettivi `*_RESULTS.md`). Se riprendi il
lavoro: leggi `FINAL_PROJECT_STATUS.md` §"Cosa resta manuale" per i prossimi passi reali (le 5 card
REVIEW, lo scheduler di sistema, Alert/Case/workflow, il wiring frontend).

Aggiornato: 2026-08-28 (vedi §6 in fondo per lo stato più recente — TASK_BETA_01 B1/B2c).
Il resto del file (§0-§5) è storia di `TASK_FIX_00_GOLDEN.md`/`TASK_FIX_01.md`, entrambi FATTI:
resta per riferimento, non serve rileggerlo per riprendere TASK_BETA_01.

---

## 0 — Stato dei tre task, in ordine

| Task | Stato |
|---|---|
| `docs/TASK_SCRAPER_PILOT.md` | **FATTO**. Pipeline v1 completa, report consegnato in chat. Corpus reale in `data/`. |
| `docs/TASK_FIX_00_GOLDEN.md` | **FATTO** (2026-08-28). Report consegnato in chat. `data/golden/golden_dataset.json` scritto: 100 item, 58 coppie, controllo a campione al 50% (18/50 errori grezzi, 9/50 sostanziali — vedi report). |
| `docs/TASK_FIX_01.md` | **FATTO** (2026-08-28). Tutti i fix (0, A-ORA, 1-5) implementati e verificati, 17/17 test verdi. Report consegnato in chat. |

---

## 1 — TASK_FIX_00_GOLDEN.md: stato fase per fase

Tutto il codice e' scritto in `pilot/golden/` (`sample.py`, `annotate.py`, `pairs.py`,
`review.py`, `review.html`, `build.py`). Nessuno di questi file va riscritto, solo eseguito
nell'ordine sotto.

- **§1 Campione stratificato** — FATTO. `data/golden/sample.jsonl` (100 item) e
  `data/golden/sampling_report.json` gia' scritti. Scostamento dichiarato: il corpus reale
  aveva solo 2 coppie duplicate-like e 13 event-like (non 20+20): shortfall di 30 item
  redistribuito su political/non_political, vedi `sampling_report.json`.

- **§2 Doppia annotazione** — FATTO ma con un bug gia' trovato e corretto.
  `data/golden/annotations_a.jsonl` (Anthropic) e `annotations_b.jsonl` (DeepSeek) esistono,
  100 righe ciascuno.
  **Bug trovato**: `deepseek-v4-pro` e' un modello "reasoning", con prompt realistici impiega
  ~50-60s a rispondere — il timeout di `pilot/llm.py` era 30s, quindi 79/100 chiamate B sono
  fallite con `_review:true, _reason:"no_response"`. **Gia' corretto**: `pilot/llm.py` ora ha
  `llm(prompt, max_tokens=800, provider=None, timeout=90)` (prima era fisso a 30s hardcoded).
  `data/golden/retry_deepseek.py` e' stato riscritto per essere **resumable**: salva su disco
  (scrittura atomica, `.tmp` + `replace`) dopo OGNI singolo item, non solo alla fine. Rilanciarlo
  (a mano o con `rerun_retry.bat`) riprende sempre dai soli item ancora `_review:true`, mai da
  capo. E' in corso in background su questo PC (lanciato con `PYTHONPATH=. python3
  data/golden/retry_deepseek.py`), e l'utente ha anche una copia zippata del progetto
  (`C:\Users\frontofficedx\Desktop\NIK 2026\media-pilot-v21-simple.zip`) con due `.bat` alla
  radice per farlo girare su un secondo PC in parallelo:
  - `run_retry.bat` — primo avvio: installa le dipendenze da `requirements.txt`, controlla che
    `.env` esista, poi lancia il retry.
  - `rerun_retry.bat` — da rilanciare ogni volta che si interrompe: stesso comando, resumable.
  **Attenzione se sono girati due retry in parallelo su due PC diversi**: ognuno scrive la
  propria copia locale di `annotations_b.jsonl`. Non vanno uniti a caso — tenere quello che ha
  finito, o quello del PC su cui si continua il lavoro, e ignorare l'altro.
  Vedi "PROSSIMO PASSO ESATTO" per come verificarne l'esito.

- **§3 Coppie candidate + giudizio** — Scritto, **non ancora eseguito**. Il pool
  (`generate_candidate_pairs`, soglia 0.35, finestra 72h) e' gia' verificato manualmente:
  8 coppie sopra soglia (1 dup-like ≥0.90, 7 event-like), pochissime per un corpus di 245 item
  reali — dichiararlo nel report finale, non e' un bug del codice. Da lanciare:
  `python -m pilot.golden.pairs --judge` (genera anche `pairs_pool.jsonl` se non lanciato
  prima senza `--judge`). Userà lo stesso `llm()` con timeout 90s: se DeepSeek e' ancora lento,
  ripetere lo stesso pattern di retry mirato usato per le annotazioni.

- **§4 UI di revisione** — Scritta (`pilot/golden/review.py` + `review.html`), **non ancora
  usata**. Va lanciata con `python -m pilot.golden.review` (apre `http://localhost:8765`)
  **dall'utente**, non da Claude: le decisioni sui disaccordi e il controllo a campione sono
  esplicitamente un passo umano (vedi "LA TRAPPOLA" nel task — se un modello risolve i propri
  disaccordi, il golden set non vale piu' niente). Salva ogni decisione subito in
  `data/golden/decisions.jsonl`, riprendibile chiudendo e riaprendo il browser.

- **§5 Consolidamento** — Scritto (`pilot/golden/build.py`), **non ancora eseguito** (aspetta
  che §3 e §4 siano completi). Produce `data/golden/golden_dataset.json` con `label_source` e
  il blocco di metriche di agreement richiesto dal report.

---

## 2 — PROSSIMO PASSO ESATTO (in ordine, non saltare)

1. Verificare l'esito di `retry_deepseek.py` (girava in background quando la sessione si e'
   fermata, lanciato come `PYTHONPATH=. python3 data/golden/retry_deepseek.py` — **non**
   `python3 data/golden/retry_deepseek.py` da solo, altrimenti `ModuleNotFoundError: pilot`,
   gia' successo una volta):
   `PYTHONIOENCODING=utf-8 python3 -c "import json; b=[json.loads(l) for l in open('data/golden/annotations_b.jsonl',encoding='utf-8')]; print(sum(1 for r in b if r.get('_review')), '/', len(b), 'ancora falliti')"`
   Se restano falliti oltre una decina, sono probabilmente prompt/articoli piu' lunghi della
   media: valutare se alzare ancora il timeout (es. 120s) o accettarli come `_review` genuini
   (finiranno comunque in coda disaccordi, decisione umana esplicita — non e' un errore fatale).
   Se e' ancora a meta': e' resumable, lanciare `PYTHONPATH=. python3 data/golden/retry_deepseek.py`
   (o `rerun_retry.bat` su Windows) e riprende dai soli item ancora falliti, nessun lavoro perso.
   Ogni chiamata reale a `deepseek-v4-pro` con un prompt di annotazione impiega ~50-60s: da zero,
   79 retry sequenziali durano **circa un'ora e un quarto**.
2. `python -m pilot.golden.pairs --judge` — genera `pairs_pool.jsonl`, `pairs_a.jsonl`,
   `pairs_b.jsonl`. Se scoppia per timeout DeepSeek, stesso pattern del punto 1 (script di
   retry mirato sulle righe con `_review:true`).
3. Dire all'utente di lanciare `python -m pilot.golden.review` e fare le decisioni via browser
   (tasti 1/2/3/spazio/freccia sinistra/s, vedi l'hint in fondo alla pagina). Claude **non deve
   farlo al posto suo** — e' il punto centrale del guardrail anti-bias del task.
4. Quando l'utente conferma di aver finito (o la UI mostra "Nessuna decisione rimasta"):
   `python -m pilot.golden.build` → scrive `data/golden/golden_dataset.json` con le metriche.
5. Controllare le due soglie del report (§5 del task):
   - se `agreement_is_political_pct` < 80 → la definizione di "politico" nel prompt e' ambigua,
     non i modelli: rivedere `ANNOTATE_PROMPT` in `pilot/golden/annotate.py` prima di continuare.
   - se `errori_trovati_nel_controllo / accordi_controllati` > 0.10 → il criterio dell'accordo
     non tiene: alzare `SPOTCHECK_FRACTION` in `pilot/golden/review.py` da 0.20 a 0.50 e rifare
     il controllo sulle righe aggiuntive.
6. Scrivere il report di FIX_00 (vedi struttura richiesta in fondo al task: decisioni umane e
   tempo costato, i tre numeri di agreement, errori trovati dal controllo, coppie sotto soglia
   risultate positive, casi "nessuna delle due" per esteso).
7. Solo dopo — iniziare `docs/TASK_FIX_01.md`, **nell'ordine scritto nel file**: FIX 0 (gia'
   fatto al punto 6) → FIX A-ORA → FIX 1 → FIX 2 → FIX 3 → FIX 4 → FIX 5. Non saltare l'ordine:
   il task lo dice esplicitamente vincolante, tre revisioni indipendenti concordavano.

---

## 3 — Cose gia' scoperte su TASK_FIX_01 (per non riscoprirle)

- **Bug "predsjedništvo 49 hit" gia' diagnosticato con causa esatta**: la card
  `predsjednistvo` in `dashboard-config.js` ha `mark:'BiH'`. Il filtro di unicita' del mark
  in `pilot/entities.py` (`build_alias_entries`, aggiunto per il bug "US Open" della run
  precedente) lascia passare `'BiH'` come alias perche' e' l'unica card con quel mark — ma
  `'BiH'` e' una sigla di paese generica, non un identificatore sicuro. In piu' `is_short_ambiguous()`
  protegge solo alias **tutto maiuscolo** (`US`, `SP`), e `'BiH'` e' maiuscolo/minuscolo misto:
  zero protezione, matcha come sottostringa ovunque. Questo e' esattamente il bug che
  TASK_FIX_01 §1b chiede di risolvere con le "tre classi di alias" (forte/frase/ambiguo) e i
  confini `\b`. Non ripartire da zero sulla diagnosi, e' gia' fatta.
- **RTRS `:443` bug confermato con numeri**: un singolo articolo con prompt realistico impiega
  ~57s su DeepSeek `deepseek-v4-pro` — utile per calibrare i timeout di `pilot/llm.py` in
  futuro (usato per il fix del punto sopra).
- Nessuna contraddizione trovata fra `TASK_FIX_01.md` e `TASK_FIX_00_GOLDEN.md`: eseguibili in
  sequenza cosi' come scritti.
- Gap di schema da colmare quando si arriva a FIX_01: quel task vuole `duplicate_of` e
  `cluster_atteso` per item nel golden set, mentre `pilot/golden/build.py` (come scritto per
  FIX_00) produce annotazioni per item + una lista `pairs` separata con etichette
  `DUPLICATO/STESSO_EVENTO/DIVERSI`. Servira' un piccolo passo di unione (union-find sulle
  coppie risolte) per derivare `duplicate_of`/`cluster_atteso` per ogni item — non e' ancora
  scritto, va fatto prima o durante FIX_01/FIX 2.

---

## 4 — Fatti chiave sull'ambiente

- `.env` esiste nella root del progetto con `ANTHROPIC_API_KEY` e `DEEPSEEK_API_KEY` (entrambe
  presenti e funzionanti, verificato con chiamate reali). **Mai stampare il contenuto di questo
  file.** `pilot/llm.py` lo carica automaticamente all'import (`_load_dotenv()`), popolando
  `os.environ` solo per le chiavi non gia' presenti.
- `llm(prompt, max_tokens=800, provider=None, timeout=90)`: `provider` esplicito
  (`"anthropic"`/`"deepseek"`) forza il provider indipendentemente da quale chiave e' presente;
  `None` mantiene la selezione automatica originaria (anthropic se c'e', altrimenti deepseek).
- Modelli usati: `claude-sonnet-5` (Anthropic), `deepseek-v4-pro` (DeepSeek) — verificati sulla
  documentazione ufficiale corrente il giorno della scrittura, non a memoria.
- Working directory del progetto (root, non `docs/`): `US/________media-pilot-v21-2026-08-26/media-pilot-v21-simple/`.
  `pilot/`, `config/`, `data/` sono li'.
- Per stampare output con caratteri cirillici su questa shell Windows, sempre
  `PYTHONIOENCODING=utf-8` prima del comando python, altrimenti `UnicodeEncodeError` su stdout
  (i file su disco sono comunque scritti correttamente in UTF-8, e' solo il terminale).
- Dipendenze installate: `feedparser`, `trafilatura`, `pytest` (quest'ultimo solo per i test,
  non e' una dipendenza della pipeline). Nessun'altra libreria: niente PyYAML (c'e' un parser
  YAML fatto a mano in `pilot/miniyaml.py` per il sottoinsieme che questo progetto scrive).

---

## 5 — File da NON toccare

Frontend (qualunque `.html`/`.css`/`.js` fuori da `pilot/golden/review.html`, che e' nostro),
`dashboard-config.js` (si legge, non si modifica), `radar.js`, `data.js`. Nessuno di questi task
lo richiede.

---

## 6 — AGGIORNAMENTO 2026-08-28 — TASK_BETA_01, dopo session limit

Ripresa da `MEDIA_PILOT_HANDOFF_RATE_LIMIT_2026-08-28.md`. Il collect a 30gg/17 fonti era già
concluso (exit 0). Fatto in questa sessione, nell'ordine:

1. **Pipeline rigenerata**: `data/raw/2026-08-28.jsonl` era più recente di `clean/items/clusters/
   scored_*` (il collect ha continuato a scrivere dopo l'ultima esecuzione della pipeline).
   Rilanciati `python -m pilot.clean` → `python -m pilot.dedup` → `python -m pilot.score`, senza
   toccare `pilot/score.py`/`config/entities.yaml`.
2. **`docs/B1_RESULTS.md` scritto** — verdetto: **FAIL sui tre criteri di B1**
   (bucket 4h 55.0% vs target ≥70%; giorno dominante 45.1% vs target ≤25%; `novelty` ancora
   `None` su 501/501, ma per costruzione — `score.py:193` la fissa a `None` incondizionatamente,
   non è un effetto della finestra). La tripla decisiva di "LA COSA PIÙ IMPORTANTE"
   (`velocity`/`novelty`/`source_diversity`) è **invariata o peggiorata**: `velocity` è tornata a
   2 valori distinti (era 3 dopo B0), i singoletti sono al 95.8% (erano 84%).
   **Trovata contaminazione temporale non prevista dal task**: 32/1284 item hanno `published_at`
   fuori dalla finestra 30gg (da `1996-01-01` a metà luglio 2026), da pagine sitemap non-articolo
   (form WordPress, recensioni auto, agenda eventi) il cui `lastmod` viene letto come data di
   pubblicazione. Gonfia `window_actual_days` di corpus a 56 (invece di ~30) e collassa
   `velocity_baseline_4h` a 1. **Non corretta**: è una decisione di prodotto (scartare l'item,
   azzerare la data, o filtrare i pattern URL non-articolo), lasciata all'utente. Dettagli e numeri
   completi in `docs/B1_RESULTS.md` §5.
3. **B2a**: DONE (invariato, vedi §4 dell'handoff rate-limit — Capital.ba e Dobojski.info via
   Wayback CDX, nessuna modifica in questa sessione).
4. **B2b Google News RSS**: NON_PASSA confermato, dichiarato in `docs/SOURCE_AUDIT.csv` (nessuna
   riapertura, come da handoff).
5. **B2c GDELT**: riga `SOURCE_AUDIT.csv` corretta. La diagnosi precedente ("timeout/handshake TLS
   su tutti i domini") era sbagliata: **`https://api.gdeltproject.org:443` non apre (riconfermato,
   timeout dopo 15s), `http://api.gdeltproject.org:80` risponde** (200 OK, ~9s, dopo un 429
   iniziale di rate-limit). Test per-paese (query `sourcecountry:BK`) ripetuto in questa sessione:
   34 articoli, 7 domini, 6 non fra le 18 fonti esistenti — conferma i numeri già nel task.
   Stato CSV: `VERIFICATO_NON_INTEGRATO` (non `NON_PASSA`: raggiungibile e utile, ma non ancora
   integrato in `collect.py` — resta a bassa priorità dopo B1, come da task).
6. **Test pipeline**: `python -m pilot.test_pipeline` → **19/19 verdi** (numero reale, invariato).
7. **B3**: NON INIZIATO. Non può partire finché la contaminazione del punto 2 non è decisa
   dall'utente — calibrare soglie su una baseline degenere non avrebbe senso.

**STOP rispettato inizialmente**; l'utente ha poi chiesto esplicitamente di segnare la
contaminazione per dopo e continuare a B3 (vedi §7).

---

## 7 — AGGIORNAMENTO 2026-08-28 (continua) — B3.1 + B3.2

Su richiesta esplicita dell'utente ("segna la contaminazione per dopo e continua"), proseguito a
B3 nonostante B1 FAIL. Dettagli completi in `docs/B3_RESULTS.md`.

- **B3.1**: golden set esteso con 111 nuove coppie dal corpus post-B1 (script nuovo
  `pilot/golden/b3.py`, non tocca i file riservati di FIX_00, scrive in `data/golden_b3/`).
  Accordo modelli 98.2%. Trovato e corretto un mix-up di tasti nella revisione umana (spotcheck
  con 1/2 invece di SPAZIO) — vedi report per il dettaglio e la trappola non corretta in
  `review.html`.
- **B3.2**: soglie ricalibrate su 162 coppie combinate (golden + golden_b3). **Trovato un secondo
  bug non pianificato**: `BL_IJ3_006` (Banjaluka24) ha un bug di estrazione — `trafilatura` incolla
  testo di articoli correlati nel corpo estratto, 71.4% degli item della fonte colpiti — che
  gonfiava artificialmente la similarità di corpo fra articoli scorrelati fino a 0.83 Jaccard.
  **Non corretto** (stesso trattamento della contaminazione B1: marcato, non risolto). Soglie
  ricalibrate escludendo questa fonte dal campione: `dedup.body_similarity_threshold` confermato
  a 0.50 (F1 0.987), `clustering.body_overlap_threshold` abbassato da 0.50 a 0.20 (F1 0.968 vs
  0.907), `window_hours` confermato a 60 (nessun positivo oltre 32h, ma censurato a 72h dal
  blocking). `max_document_frequency` **non toccato**: il gap che giustificava 0.10 è sparito sul
  corpus allargato (continuum di document frequency, non più due outlier netti) — decisione di
  prodotto lasciata all'utente, non presa qui.
- **B3.3** (rimisurare le metriche FIX_01 sul corpus nuovo — `is_political`, precisione entità,
  precisione clustering): **NON INIZIATO**. Prossimo passo.
- **B4** (dashboard oltre `rassegna.json`): non toccato in questo giro.

**Due contaminazioni ora aperte e marcate per dopo**, entrambe quantificate ma non corrette:
1. B1 §5 — `published_at` falsi da sitemap non-articolo (32/1284 item, 3 fonti: BIH_ELEC_002,
   BL_IJ3_002, ECO_001).
2. B3.2 — testo contaminato da articoli correlati incollati, BL_IJ3_006/Banjaluka24 (100/140 item,
   71.4% di quella fonte).

Nessuna delle due tocca `pilot/score.py`/`dashboard-config.js`/`config/entities.yaml` (restano
riservati). Entrambe richiedono una decisione dell'utente su COME correggere (tre opzioni diverse
per B1, riscrivere l'estrazione per B3), non SE correggere — non decise qui.

---

## 8 — AGGIORNAMENTO 2026-08-28 (continua) — la contaminazione B1 è stata risolta da un'altra sessione

Durante il lavoro su B3.2, una **sessione parallela** ha modificato `pilot/clean.py` (mtime 05:22)
e `pilot/collect.py` (mtime 05:24) aggiungendo `out_of_window()`: scarta in `clean()` gli item con
`published_at` fuori da `BACKFILL_DAYS_DEFAULT ± 1gg` da `scraped_at` (item senza data restano,
regola "zero invenzione"). **Risolve esattamente la contaminazione di B1 §5** — stessa diagnosi,
fix diverso da quelli che avevo elencato come opzioni per l'utente.

Integrato, non sovrascritto: rigenerata la pipeline (`clean`→`dedup`→`score`) sul nuovo
`clean.jsonl` (1488, non più 1528) e rimisurato tutto. Risultato, dettagli in `docs/B1_RESULTS.md`
("AGGIORNAMENTO" in cima al file):

- `window_actual_days` di corpus: **30** (era 56, ora combacia con `BACKFILL_DAYS_DEFAULT`)
- `velocity`: **4 valori distinti** (0.0/1.0/2.0/3.0) — soddisfa il criterio B0, non soddisfatto
  sotto contaminazione
- singoletti: **83.2%** (era 95.8% sotto contaminazione, 84% il riferimento pre-B1/B2) — nota:
  cumula anche l'effetto di `clustering.body_overlap_threshold` abbassato a 0.20 in B3.2
- bucket 4h (55.0%) e giorno dominante (45.1%): **invariati, restano FAIL** — il fix scarta solo
  40/1488 item (2.7%), non tocca la concentrazione sull'ultimo giorno

`config/sources.yaml` riscritto dalla stessa sessione parallela con `window_actual_days` per fonte
ricalcolati sul dato pulito (es. BIH_ELEC_002 34→5, ECO_001 20→9) — verificato che
`compute_window_actual_days()` corrente coincide col file su disco.

**Osservazione, non investigata**: `pilot/export_dashboard.py` risulta modificato (mtime 05:49),
in parallelo a questa sessione. Probabile lavoro B4 (dashboard) di un'altra sessione, coerente con
"B0/B4a lavorati in parallelo" già visto in `TASK_BETA_01.md`. Non toccato, non verificato nel
dettaglio — fuori scope per questa sessione (B1/B3).

**Test**: `python -m pilot.test_pipeline` → 19/19 verdi anche dopo tutti questi cambi.

**Stato finale di questa sessione (prima di passare a TASK_BETA_02)**: B1 contaminazione risolta
(da altri) e reintegrata; B2 invariato; B3.1 (golden set esteso) e B3.2 (soglie ricalibrate su
Jaccard) fatti, con una seconda contaminazione nuova trovata e NON risolta (BL_IJ3_006/
Banjaluka24, bug di estrazione trafilatura). B3.3 assorbito in TASK_BETA_02 C2, non fatto a
parte.

---

## 9 — AGGIORNAMENTO 2026-08-28 — passaggio a TASK_BETA_02, C1 fatto

`docs/TASK_BETA_02.md` (scritto da un'altra sessione, sostituisce esplicitamente la parte non
fatta di TASK_BETA_01) letto e ripreso su richiesta dell'utente. **C0 era già fatto** da quella
stessa sessione (`pilot/export_dashboard.py`, mtime 05:49, notato in §8 sopra). Fatto in questa
sessione: **C1 — sostituita la metrica di similarità di corpo**, Jaccard su n-grammi → TF-IDF +
coseno (`pilot/dedup.py`). Dettagli completi, inclusa la scoperta che dedup e clustering
richiedono soglie separate sulla nuova metrica (0.80 e 0.20) e che BL_IJ3_006 resta un rischio
noto anche col coseno (più robusto, non immune), in `docs/TASK_BETA_02_RESULTS.md`.

Risultato sul corpus: cluster 382→334, singoletti 83,2%→80,5%, `velocity` 4 valori (nuovo massimo
7.0), `source_jump` 3,0% (era <1%). `signal_score` resta a **16 valori distinti** — atteso, è
lavoro di C3, non di C1. Test: 19/19.

`docs/B3_RESULTS.md` marcato come superato da C1 per la parte di calibrazione soglie (B3.1,
l'estensione del golden set, resta valida e riusata per la calibrazione di C1).

**Non fatto**: C0b, C2 (ricalibrazione post-C1 + rimisurare FIX_01 + difetto passaggi dedup
chiusi), C3 (punteggio onesto), C4 (backfill), C5 (GDELT), C6 (run unica + `BETA_RESULTS.md`).
Prossimo passo naturale: C2.

---

## 7 — RETTIFICA 2026-08-28 (sessione di verifica) — §6.7 era sbagliato

`B1_RESULTS.md` §5 e `HANDOFF_PROGRESS.md` §6.7 dicevano che B3 non poteva partire finché la
contaminazione temporale non fosse decisa, perché avrebbe collassato `velocity_baseline_4h` a 1.
**Misurato e smentito**: sulla finestra pulita a 30gg la mediana dei bucket da 4h è 1, quindi
`baseline_4h = max(1,1) = 1` — **identico** al corpus contaminato. Vedi `B1_RESULTS.md` §8.

- La contaminazione (26 item fuori finestra) sporca solo `window_actual_days` (56 vs 31) e i valori
  per fonte in `config/sources.yaml`. Non tocca `velocity`, `baseline_4h`, `baseline_incomplete`.
- `velocity` ha 2 valori perché **8 cluster su 501 hanno mai 2 articoli entro 4h** — densità, non
  denominatore, non finestra.
- Il salto dei singoletti non viene dal filtro DF di B4a (disattivarlo dà 94.7% e riapre un cluster
  da 63 item) né dalla finestra a 30gg (sugli ultimi 7gg: 93.4%).

**Stato reale: B3 non è bloccato dalla contaminazione.** Ma il collo di bottiglia misurato è la
sovrapposizione fra fonti, cioè **B2b/B2c**, non la ricalibrazione. Le due voci contraddittorie
(`B1_RESULTS.md` chiusura "rimandata a dopo B3" vs §6.7 "non può partire") sono entrambe superate
da questa rettifica.

## 8 — 2026-08-28, seguito della verifica: causa isolata, RFC 02 scritta

La §7 diceva che il collo di bottiglia era la sovrapposizione fra fonti (quindi B2). **Sbagliato**,
misurato subito dopo: sui 218 item dei 2 giorni piu' densi ci sono 1.430 coppie cross-fonte con
titolo simile o entita' condivise, incluse coppie a titolo IDENTICO. Le fonti si sovrappongono
eccome. Escluse anche, con numeri: filtro DF (94,7% senza), filtro di rilevanza (94,8% ignorandolo).

Causa vera isolata: **`clustering.body_overlap_threshold: 0.50` non scatta mai su una coppia vera.**
Su 16 coppie cross-fonte a titolo quasi identico (stesso evento certo) il Jaccard del corpo va da
0.184 a 0.374, mediana 0.245: **0 su 16 sopra 0.50**. Sweep offline: body 0.20 porta i singoletti
da 95,8% a 83,8%. Costo in precisione non misurabile col golden set attuale (n=3 stesso-evento).

Secondo fatto: **il backfill a 30gg e' riuscito su UNA fonte sola** (BL_IJ3_002, 28 giorni). Le
solo-RSS danno 1-2 giorni. Mediana fonti attive/giorno: 3 su 17.

Terzo: `velocity` ha un tetto strutturale — 8 cluster su 501 hanno mai 2 articoli entro 4h.

Difetto di codice trovato: i passaggi del dedup sono chiusi (un item `used` al passaggio 2/3 non puo'
piu' essere agganciato dal passaggio 4 a titolo >=0.90): 12 coppie a `title_norm` identico
sopravvivono come item distinti.

Tutto in **`docs/RFC_SECONDA_OPINIONE_02.md`**, autosufficiente, da dare a un'altra AI.
Nessun file di codice o config modificato in questa verifica.

## 9 — 2026-08-28: filtro temporale applicato, B1 resta FAIL

Applicato il filtro deciso dall'utente: `pilot/clean.py` scarta gli item con `published_at` fuori
dalla finestra di 30gg (`out_of_window`, tolleranza ±1g; item senza data si tengono). Stesso guard
riusato in `collect.py:compute_window_actual_days`, altrimenti `config/sources.yaml` restava sporco.
Scartati 40 item raw su 1627, da 4 fonti. Pipeline rilanciata, test **19/19**.

Risultato: `window_actual_days` 56 → **30**, `sources.yaml` corretto su 4 fonti (34→27, 20→9, 16→5,
9→7), span corpus 1996→2026 diventa 2026-07-29 → 2026-08-27.
**I tre criteri di B1 non si muovono di un decimale**: bucket 4h 55.0% (identico), giorno dominante
45.1% (identico), `novelty` None su 489/489, `baseline_4h` = 1, `velocity` 2 valori, singoletti
95.7%, `signal_score` 16 valori distinti. Tabelle in `B1_RESULTS.md` §9.

**Quindi: la contaminazione non era il blocco di B3, e non lo era neanche prima.** La causa misurata
del ranking piatto e' `clustering.body_overlap_threshold: 0.50` (mai attiva su una coppia vera).
Prossimo passo proposto: costruire il golden set dalle coppie cross-fonte a titolo identico
(positivi certi, deterministici, senza LLM) e ricalibrare la soglia misurando la precisione.
Vedi `docs/RFC_SECONDA_OPINIONE_02.md`.

## 10 — 2026-08-28: la metrica di similarita' e' sbagliata, non la soglia

Ricerca su come lo fanno i progetti simili (Europe Media Monitor, NewsCatcher, letteratura news
story clustering): standard unico = **TF-IDF + coseno su titolo+corpo dentro una finestra
temporale**. Nessuno usa Jaccard su n-grammi di caratteri del corpo.

Motivo: il Jaccard non e' normalizzato per lunghezza. Un sommario RSS da 250 char contro l'articolo
da 2.000 char sullo stesso evento non puo' superare ~250/2000 = 0.12. Misurato sul corpus:
il Jaccard dei positivi segue il rapporto di lunghezza quasi linearmente.

Confronto misurato (16 coppie confermate stesso-evento vs 2.000 coppie a caso), TF-IDF coseno
scritto in 15 righe di stdlib:

  Jaccard char-4gram : positivi 0.184-0.374 | negativi max 0.334  -> SI SOVRAPPONGONO
  TF-IDF coseno      : positivi 0.472-0.699 | negativi p95 0.056  -> separa, margine 8x

**Quindi abbassare `body_overlap_threshold` a 0.20 sarebbe stato sbagliato**: sotto 0.334 si fondono
coppie scorrelate. Non esiste una soglia buona per quella metrica. Con il coseno, soglia 0.35-0.45.

Il golden set si costruisce gratis: positivi = coppie cross-fonte a titolo quasi identico,
negativi = coppie a caso. Deterministico, senza LLM, gia' dentro il corpus.

Prossimo passo proposto: sostituire la prova del corpo in `pilot/dedup.py` (`char_shingles`/
`jaccard`) con TF-IDF coseno su titolo+corpo, soglia 0.40, e ricalibrare con quei due insiemi.
Dettagli e tabelle: `docs/RFC_SECONDA_OPINIONE_02.md` §8.

**NOTA 2026-08-28 (sessione successiva): questo §10 era gia' superato quando scritto.** Chi lo ha
scritto non sapeva che TASK_BETA_02 §C1 aveva GIA' fatto esattamente questa sostituzione (stessa
sessione, poco prima): `pilot/dedup.py` usa TF-IDF+coseno da `TASK_BETA_02_RESULTS.md` C1 in poi,
non piu' Jaccard. `body_overlap_threshold: 0.20` e `body_similarity_threshold: 0.80` in
`config/scoring.yaml` sono gia' calibrati su n=110/162 (non 0.40 - due soglie diverse per dedup e
clustering, vedi C1). Non ripartire da questo §10: e' storia, non un passo aperto. Stato corrente
completo in `docs/TASK_BETA_02_RESULTS.md` (C1-C3 fatti) e `docs/TASK_BETA_02.md`.
