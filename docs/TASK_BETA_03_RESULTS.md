# TASK BETA 03 RESULTS

Date: 2026-08-29. Eseguito D0 (D0.1, D0.2) e D1, D2.1, D2.2 di `MEDIA_PILOT_NEXT_TASKS_AFTER_BETA02.md`.
**STOP dopo questo file**, come richiesto — E1+ (BETA 04) non iniziato.

Non riaperti: C1/C2/C3 di TASK_BETA_02 (nessuna regressione trovata che lo richiedesse), i pesi di
`signal_score` (invariati, non toccati per inseguire piu' valori distinti).

Suggerimento applicato per fare prima, senza saltare passi: D0.1 (fix locale, CPU-bound) e D0.2
(rete, I/O-bound) sono indipendenti — eseguiti in parallelo invece che in sequenza (job in
background mentre si scriveva/verificava l'altro).

---

## D0.1 — Banjaluka24 (BL_IJ3_006): causa isolata, fix mirato

**Causa esatta** (non solo confermata, misurata riga per riga): il template del sito appende in
coda all'articolo un widget "altri articoli" che `trafilatura` non isola. Firma strutturale
identica su ogni occorrenza: una riga `-` seguita da una riga indentata a tab
`CategoriaNdana ago<titolo>` (es. `Politika2 dana agoKAD "SVETAC"...`, `Hronika1 dan ago...`),
sempre nell'ultimo 15-22% del testo estratto.

**Fix**: `pilot/clean.py`, nuova funzione `strip_source_specific(source_id, text)` applicata SOLO
a `BL_IJ3_006`, chiamata prima di `strip_boilerplate()` in `clean_item()`. Taglia il testo alla
prima occorrenza del pattern (regex sull'intera firma, non solo sulle singole parole, per non
rischiare falsi positivi su un trattino di lista normale in un'altra fonte — verificato: 0 falsi
positivi sulle altre 16 fonti, la guardia e' comunque `source_id == "BL_IJ3_006"`).
Verificato PRIMA di applicarlo: nessuno dei 100 item contaminati scende sotto `MIN_TEXT_LEN=200`
dopo il taglio — non si crea nuovo `EMPTY_CONTENT`.

**Prima/dopo**, misurato su `data/clean.jsonl` (140 item della fonte):

| | prima | dopo |
|---|---:|---:|
| item contaminati dal widget | 100/140 = **71,4%** | **0/140 = 0%** |

Nessuna regressione sulle altre fonti (per costruzione: `source_id` esplicito, non un pattern
generico). Test aggiunto: `test_4b_bl_ij3_006_widget_stripped_other_sources_untouched` (verifica
sia il taglio sulla fonte giusta, sia che una lista puntata normale su un'altra fonte non venga
toccata).

**Non fatto**: ricalibrare le soglie di dedup/clustering sul corpo ora pulito di questa fonte
(C1/C2 di TASK_BETA_02 restano quelli — nessuna regressione dimostrata che lo richieda, la task
list lo esclude esplicitamente "salvo regressione dimostrata"). La calibrazione C1 aveva gia'
escluso BL_IJ3_006 dal campione proprio per questa contaminazione: resta un miglioramento del
corpo reale che alimenta quelle soglie, non un motivo per ricalibrarle di nuovo.

---

## D0.2 — secondo giro di backfill + audit RTRS

### Fix di codice necessario, dichiarato prima di lanciare il giro

Misurato PRIMA di lanciare il secondo giro: le funzioni di backfill (`collect_from_sitemap_backfill`,
`collect_from_wayback_cdx`) troncano sempre a `MAX_BACKFILL_URLS=100` selezionando i candidati PIU'
RECENTI — un secondo giro naive avrebbe riselezionato la STESSA finestra, zero item nuovi (verificato
per costruzione, non solo per ipotesi). Aggiunto un parametro opzionale `exclude_canonical` (default
`None`, **nessun cambiamento di comportamento per il collect quotidiano**) che salta gli URL
canonici gia' raccolti PRIMA del troncamento, cosi' il secondo giro raggiunge la storia successiva
invece di ripetere la prima. Filo passato attraverso `collect_from_html_source` e
`collect_supplemental_history`. Nessun nuovo scraper, nessuna soglia di clustering toccata.

### Secondo giro — 4 fonti (RS_ENT_002, SRC_009, FBIH_001, BL_IJ3_003)

| fonte | giorni dopo 1o giro (C4) | item 2o giro | giorni dopo 2o giro |
|---|---:|---:|---:|
| RS_ENT_002 | 7 | 100 | 7 |
| BL_IJ3_003 | 2 | 100 | 2 |
| SRC_009 | 2 | 80 (sitemap esaurito prima di 100) | 2 |
| FBIH_001 | 2 | 100 | 2 |

**380 nuovi item, tutti genuinamente nuovi** (0 duplicati, `exclude_canonical` verificato
funzionante). **Nessuna delle 4 fonti guadagna un giorno in piu'**: il volume raddoppia ma
resta nella stessa finestra temporale gia' coperta — sitemap/Wayback per queste fonti non
raggiungono indietro nel tempo, danno solo piu' densita' sugli stessi giorni. Dichiarato,
non nascosto: un terzo giro con lo stesso metodo non cambierebbe la mediana di copertura.

### Audit RTRS (RS_ENT_001) — nessun metodo HTTP stabile trovato

- `robots.txt`: 69 byte, nessuna riga `Sitemap:`.
- `/sitemap.xml`, `/sitemap_index.xml`, `/sitemap-vijesti.xml`: tutti HTTP 404.
- Il feed RSS stesso (`/vijesti/rss.php`, gia' in uso): 100 entry, ma copre **da solo meno di 12
  ore** (RTRS pubblica ad altissimo volume — 100 vijesti in mezza giornata). Non e' un problema di
  raccolta: e' il volume della fonte che rende il feed una finestra corta per costruzione.
- Wayback CDX (gia' provato in C4): 0 item nuovi nella finestra.

**Limite dichiarato, non forzato**: nessun metodo HTTP semplice e stabile porta RTRS oltre i 2
giorni gia' misurati. Non costruita browser automation (vietato dal task). RTRS resta la fonte con
la storia piu' corta del corpus, insieme alle altre 3.

### Risultato aggregato

| | prima (dopo C4) | dopo D0.2 |
|---|---:|---:|
| raw totali | 2.027 | **2.407** |
| mediana fonti attive/giorno | 5,5 | **5,5 — invariata** |

Confermato quanto gia' scritto in `BETA_RESULTS.md` C4: il backfill vale volume, non copertura
temporale, per queste 4 fonti specifiche. Il bersaglio di mediana >=8 dichiarato dal task **non e'
raggiungibile con questo metodo su queste fonti** — servirebbe un archivio storico diverso da
sitemap/Wayback per RTRS/N1/Klix/Glas Srpske, fuori dai vincoli del task (niente browser
automation, niente nuovi scraper).

---

## D1 — Trending Engine per entita' (`pilot/trending.py`)

### Decisione architetturale presa PRIMA di scrivere lo schema (come richiesto dal task)

Letto `assets/data/trending.json` (il file reale) E tracciato `radar.js` prima di disegnare
qualunque schema. Scoperta che cambia l'approccio: **`RadarEngine.trending()` non legge
`trending.json` come "lista di trending gia' calcolati".** Lo tratta come altri item da versare
nello stesso pool di `rassegna.json`, e ricalcola DA SOLO la sua nozione di trending (ripetizione
di modulo fra articoli, soglia `TRENDING_VELOCITY_MIN=4`, o source jump locale->nazionale —
`radar.js` righe 42-150) — un meccanismo completamente diverso da "mentions/eventi/fonti per
entita' nel tempo" che il task chiede.

**Conseguenza**: un "adapter" che scrivesse l'output di questo motore nello schema-item di
`trending.json` (title/menu/date/modules) dovrebbe INVENTARE quei campi per un oggetto che non e'
un articolo — esattamente cio' che "zero invenzione" vieta, e il genere di scorciatoia che il
resto del progetto ha sempre rifiutato (vedi `_JUDGMENT_DEFAULTS` in `export_dashboard.py`, mai
forzato uno schema che non calza). **Deciso**: non scrivere l'adapter verso `assets/data/trending.json`
in questo task. Il file demo esistente non viene toccato (resta la fonte per il funnel di
`RadarEngine`, invariato). L'output nuovo e reale vive in `data/trending_entities.jsonl`, un
livello che oggi il frontend non consuma ancora — collegarlo e' una decisione di prodotto
(serve o un nuovo tab "Trending per entita'" in UI, o un adapter dichiaratamente diverso dallo
schema-articolo), lasciata all'utente, non presa qui.

### Cosa calcola (`pilot/trending.py`, legge `data/scored_items.jsonl`)

Per ognuna delle 55 entita' del registry (mai una nuova inventata): `mentions_1h/4h/24h`,
`unique_events_4h/24h` (cluster distinti), `unique_sources_4h/24h` (owner_group distinti, stessa
logica di `source_diversity`), `acceleration` (mentions_4h / baseline_7d), `baseline_7d` (mediana
di mention/bucket-4h sugli ultimi 7 giorni, bucket vuoti inclusi — stesso principio B0 di
`velocity_baseline_4h`, clampata a 1 per lo stesso motivo: una mediana 0 non e' "nessun ritmo", e'
il minimo misurabile), `share_of_voice_24h`, `last_event_at`, `evidence` (i cluster con piu'
mention nella finestra, con URL e titolo reali).

**Guardia aggiunta durante lo sviluppo, non nella spec originale**: `baseline_7d` resta `None` per
OGNI entita' se il CORPUS stesso non copre 7 giorni civili — non solo quando la singola entita' non
ha mention, altrimenti i bucket prima dell'inizio della raccolta contano come "silenzio" invece che
"dato mancante" e la mediana sottostima il ritmo normale. `baseline_30d` resta sempre `None` in
questo task, dichiarato: nessuna fonte ha 30gg di copertura piena su tutte le entita' (mediana 5,5
fonti attive/giorno, vedi D0.2) — calcolarlo sarebbe un'invenzione.

### Risultato misurato

Sul corpus finale (683 item rilevanti, 462 cluster): **55/55 entita' nel registry**, **24 con
almeno una mention nelle ultime 24h**, **29 con `baseline_7d` misurabile** (le altre: zero mention
negli ultimi 7gg, `None` corretto).

Top per `acceleration` (poi `mentions_24h`):

| entita' | acceleration | mentions_24h | eventi_24h | fonti_24h |
|---|---:|---:|---:|---:|
| dodik | 5.0 | 27 | 21 | 5 |
| banjaluka | 5.0 | 19 | 15 | 3 |
| beograd | 3.0 | 24 | 17 | 4 |
| ij5-konkurencija | 3.0 | 23 | 19 | 4 |
| finansiranje | 3.0 | 16 | 15 | 4 |
| predsjednistvo | 3.0 | 13 | 11 | 4 |
| us-snsd / snsd | 3.0 | 10 | 9 | 4 |
| opozicija | 3.0 | 10 | 9 | 5 |
| sds | 3.0 | 5 | 4 | 4 |
| minic | 2.0 | 12 | 8 | 4 |
| stevandic | 2.0 | 8 | 6 | 3 |
| predsjednik-rs / stanivukovic | 1.0 | 10 / 9 | 9 | 5 |

**Nota onesta sul numero**: quasi tutte le `baseline_7d` misurate sono clampate a 1 (la maggior
parte dei bucket da 4h e' vuota anche per le entita' piu' citate — 55 entita' su un corpus di 683
item non riempiono 42 bucket/settimana). `acceleration` oggi e' quindi vicino a `mentions_4h` per
molte entita', non una vera "accelerazione rispetto a un ritmo consolidato": e' un limite del
volume del corpus (stesso problema gia' documentato per `velocity`/`trending_now` in
`BETA_RESULTS.md`), non del codice. Test: `test_14_trending_acceleration_needs_baseline_and_recent_burst`.

---

## D2.1 — Audit delle 9 card senza `modules`

Nessun file toccato (`dashboard-config.js` resta letto, non scritto — decisione frontend
card-per-card, esplicitamente fuori scope pilot per `HANDOFF_PROGRESS.md` §5 / `TASK_BETA_02.md`
C0b). Tabella di audit, azione raccomandata non applicata:

| card | entita'/alias esistono? | evidenza nel config | mapping sicuro? | azione |
|---|---|---|---|---|
| `doboj` | sì (territory) | `type:'territory'`, stesso tipo delle 9 card IJ generate dinamicamente da `build_territory_cards()`, che HANNO GIA' `modules:['IJ']` per costruzione | sì — stesso pattern, sembra un'omissione nella card letterale, non una scelta diversa | **MAP** → `['IJ']` |
| `banjaluka` | sì (territory) | idem | sì, stesso motivo | **MAP** → `['IJ']` |
| `josic` | sì (actor) | `mark:'SNSD'` gia' dichiarato nella card stessa (non dedotto dal nome) | sì — dal campo strutturato `mark`, non dal testo | **MAP** → `['SNSD']` |
| `obren` | sì (actor) | `mark:'SNSD'` gia' dichiarato | sì, stesso motivo | **MAP** → `['SNSD']` |
| `predsjednistvo` | sì (race) | candidati Cvijanović/Božović/Vukanović nel `meta`, ma le loro affiliazioni di partito non sono un campo strutturato nel config | no — servirebbe sapere il partito di ciascun candidato, non deducibile da qui | **REVIEW** |
| `finansiranje` | sì (institution) | il `meta` dice "OHR mjera per SNSD e US" ma e' testo descrittivo, non struttura | parziale — il meta suggerisce `['SNSD','US']` ma e' prosa, non un campo | **REVIEW** |
| `sps` | sì (party) | `mark:'SPS'` non e' un codice riconosciuto nel vocabolario di `radar.js` (`POLITICAL_MODULES`/`LOCAL_MODULES`/...) | no | **REVIEW** |
| `sp-demos` | sì (party) | `mark:'SP'`, stesso problema | no | **REVIEW** |
| `dns-nps` | sì (party) | `mark:'DNS'`, stesso problema | no | **REVIEW** |

**Done di D2.1**: le 9 card hanno una decisione esplicita (4 MAP, 5 REVIEW) — nessun mapping
applicato al codice, la task lo chiede solo come raccomandazione (azioni ammesse includono
esplicitamente `REVIEW`, e "non dedurre codici politici solo dal nome della card" esclude proprio
i 5 casi lasciati REVIEW). Copertura card rimisurata sul corpus finale: **471/683 = 69%** (era
76% su un corpus piu' piccolo — il calo e' diluizione da piu' item, non un peggioramento della
mappatura: le stesse 9 card mancano, nessuna in piu').

---

## D2.2 — Entity salience (misura, non sostituzione)

`pilot/entity_salience.py`, legge `data/items.jsonl` (ha `_entity_hits`/`cluster_id`), scrive
`data/entity_salience.jsonl`. **Non tocca `score.py`/`scoring.yaml`**: e' la misura richiesta dal
task prima di decidere se sostituire `entity_centrality`, non un'integrazione.

`entity_centrality` esistente e' gia', di fatto, "trovato in titolo (1.0) / lead (0.6) / corpo
(0.3) / mai (0.0)" — 4 livelli per costruzione (`match_entities` in `entities.py`). `entity_salience`
aggiunge, per (item, entita'): `occurrence_count` (quante volte l'alias ricorre nel testo),
`co_entities_in_event` (quante altre entita' nello stesso cluster), `is_primary_in_event`
(e' l'entita' con la centralita' massima del suo cluster).

**Risultato misurato** sul corpus finale (683 item rilevanti, 462 cluster):

| | `entity_centrality` (esistente) | `entity_salience` (nuovo) |
|---|---:|---:|
| valori distinti (item, entita') | 3 (su questo giro: nessun hit "lead" osservato) | **22** |
| valori distinti di MAX per cluster | non rimisurato a parte (era 4 su tutto il corpus in BETA_RESULTS.md) | **13** |

Piu' granulare, misurato — non sostituito nel punteggio in questo task, come richiesto. Test:
`test_15_entity_salience_more_granular_than_four_levels`.

---

## Test e ripetibilità

`python -m pilot.test_pipeline`: **23/23 verdi** (era 20/20 prima di BETA 03: +3 nuovi —
`test_4b` per D0.1, `test_14`/`test_15` per D1/D2.2).
`python -m pilot.run_all --no-collect` rigenera l'intera catena in un comando, invariato da C6.

Corpus finale (dopo D0.1 + D0.2, prima di D1/D2 che non toccano il corpus):

| stadio | conteggio |
|---|---:|
| raw | 2.407 (era 2.027) |
| clean | 2.267 |
| dedup | 1.947 |
| rilevanti | 683 |
| cluster | 462 |
| con card dashboard | 471 = 69% |

---

## STOP — riepilogo per la revisione richiesta

- **Qualità Banjaluka24**: contaminazione 71,4% → **0%**, fix mirato alla fonte, zero regressioni.
- **Copertura storica**: +380 item genuinamente nuovi, mediana fonti attive/giorno **invariata a
  5,5** (il metodo sitemap/Wayback ha raggiunto il suo limite su queste 4 fonti; RTRS audit fatto,
  nessun metodo HTTP stabile trovato, limite dichiarato).
- **Distribuzione Trending**: 55 entità, 24 attive nelle ultime 24h, 29 con baseline misurabile;
  top per acceleration in tabella sopra. Adapter verso `assets/data/trending.json` **non scritto**
  per un motivo architetturale scoperto tracciando `radar.js` (vedi D1) — decisione lasciata
  all'utente, non un lavoro rimandato per pigrizia.
- **Top 20 entità per momentum**: tabella in D1 (12 righe con dati reali, le altre 43 hanno
  `acceleration=0` o `None` — non c'è un ventesimo valore significativo da mostrare, dichiarato
  invece di riempire con zeri).
- **Copertura card**: 471/683 = 69%, audit delle 9 card mancanti fatto (4 MAP raccomandate, 5
  REVIEW), nessun mapping applicato al codice.
- **Test**: 23/23.

Nessun Alert/Case/giudizio politico generato. Nessuna nuova entità inventata. `baseline_30d`
resta `None`. Pronto per la revisione umana prima di iniziare BETA 04.
