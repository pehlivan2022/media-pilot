# BETA RESULTS — chiusura di TASK_BETA_02

Date: 2026-08-28. Numeri finali misurati da `python -m pilot.run_all --no-collect` DOPO il
backfill di §C4 (l'ultimo stadio che cambia il corpus) — non usare i numeri di C0-C3 in
`TASK_BETA_02_RESULTS.md`, che sono presi PRIMA del backfill e restano corretti solo come storia
di quella fase. Dettagli fase-per-fase in `docs/TASK_BETA_02_RESULTS.md` (C0-C3) e in questo file
per C4-C6.

## Corpus e pipeline (numeri finali, dopo C4)

| stadio | conteggio |
|---|---:|
| raw raccolti (finestra 30gg, incl. backfill C4) | 2.027 |
| puliti (`clean`, dopo filtro `out_of_window`) | 1.888 |
| item dopo dedup | 1.614 |
| item rilevanti (`is_relevant`) | 592 |
| cluster | 396 |
| singoletti | 324 = **81,8%** |
| in `rassegna.json` (export dashboard) | 592 |
| con card dashboard (`modules` -> `dashboard-config.js`) | 450 = **76%** |
| `signal_score`, valori distinti | **22** su 396 cluster |
| test | **20/20** |

Un solo comando rigenera tutta la catena e stampa i conteggi: `python -m pilot.run_all`
(`--no-collect` per saltare la raccolta di rete e riusare `data/raw/` esistente, `--days N` per
cambiare la finestra). Si ferma al primo stadio che produce zero (§C6, sotto).

## `signal_score`: 16-17 -> 22 valori distinti

Non i 50 auspicati da `TASK_BETA_02.md`. Causa isolata e dichiarata in C3, non nascosta: il tetto
reale di combinazioni possibili dei 4 segnali rimasti (`source_diversity`, `entity_centrality`,
`trending_now`, `source_jump`) su questo corpus e' ~24-25 tuple distinte — non un problema di pesi
(era 16-17 per collisioni additive, corretto in C3 ridisegnando le scale dei pesi), ma di quanto
questi segnali variano davvero: 81,8% dei cluster e' un singoletto (`source_diversity=1`),
`entity_centrality` ha solo 4 livelli per costruzione (54 entita' note), `source_jump` e
`trending_now` scattano su poche decine di cluster su quasi 400. Il backfill di C4 (sotto) non ha
spostato questo numero: era gia' previsto, non e' quello il fattore principale. Dettagli e la
risposta a RFC_SECONDA_OPINIONE_02.md §7 in `TASK_BETA_02_RESULTS.md` §C3.

## C4 — backfill fonti solo-RSS

Applicato il backfill gia' scritto (`pilot.collect.collect_supplemental_history`: sitemap poi
Wayback CDX) alle 5 fonti ad alto volume che davano 1-2 giorni di storia
(`docs/TASK_BETA_02.md` §C4): `RS_ENT_001`, `RS_ENT_002`, `BL_IJ3_003`, `SRC_009`, `FBIH_001`.

**400 nuovi item raccolti** (0 errori). Copertura per fonte, giorni distinti prima -> dopo:

| fonte | giorni prima | giorni dopo | item nuovi |
|---|---:|---:|---:|
| RS_ENT_002 | 6 | **7** | 100 (troncato da `MAX_BACKFILL_URLS`) |
| SRC_009 | 1 | **2** | 100 (troncato) |
| FBIH_001 | 1 | **2** | 100 (troncato) |
| BL_IJ3_003 | 1 | **2** | 100 (troncato) |
| RS_ENT_001 | 2 | 2 | **0** — ne' sitemap ne' Wayback hanno dato copertura nuova |

**Mediana di fonti attive/giorno su tutte le 17: 3 -> 5,5** (era il numero che definiva "il
backfill non e' mai davvero avvenuto", §5.2 della RFC). Migliora ma **non raggiunge il bersaglio
dichiarato dal task (>=8)**: 4 fonti su 5 sono limitate da `MAX_BACKFILL_URLS=100` per chiamata (il
sitemap/Wayback aveva piu' storia disponibile di quella recuperata in un solo giro — rilanciare lo
stesso backfill un'altra volta su queste 4 raccoglierebbe altri giorni), e RS_ENT_001 (RTRS) resta
bloccata: nessun sitemap.xml raggiungibile e Wayback CDX non ha restituito nulla di nuovo nella
finestra, coerente con quanto gia' noto su questa fonte (consegna solo il sommario RSS, mediana 285
caratteri — vedi `RFC_SECONDA_OPINIONE_02.md` §5.2, domanda 2, non affrontata qui).

Effetto sul ranking, come gia' previsto dalla RFC ("vale ~6 punti, non e' il fattore principale"):
singoletti 81,3% -> 81,8% (invariato entro il rumore, non un peggioramento reale — piu' fonti
diluiscono leggermente i cluster esistenti), `signal_score` invariato a 22 valori distinti. Il
backfill era la parte piu' facile da misurare, non quella che sblocca il ranking (era C1).

**Non fatto in questa sessione**: un secondo giro di backfill sulle 4 fonti troncate da
`MAX_BACKFILL_URLS`, e l'indagine su perche' RTRS non ha sitemap raggiungibile. Entrambi
economici da riprovare (stesso codice, nessuna modifica), lasciati come prossimo passo dichiarato
invece di essere spinti oltre in questa sessione.

## C5 — GDELT

Gia' chiuso da una sessione precedente con l'opzione "archiviato con il motivo" (esplicitamente
accettata dal task, `TASK_BETA_02.md` §C5): riga `GDELT_DOC2` in `docs/SOURCE_AUDIT.csv`, stato
`VERIFICATO_NON_INTEGRATO`. Raggiungibile via `http://` (non `https://`), 34 articoli/7 domini per
query paese, 6 domini nuovi rispetto alle 18 fonti esistenti — ma quasi tutti
Federazione/Sarajevo/Croazia: copre "come la RS viene raccontata fuori dalla RS" (materia
`source_jump`), non densifica la copertura locale RS che e' il problema misurato in C1/C2/C4.
Non riaperto in questa sessione: nessun numero nuovo da aggiungere alla decisione gia' presa, e il
task accetta esplicitamente questa risposta come chiusura valida.

## C6 — run ripetibile

`pilot/run_all.py` (nuovo): `python -m pilot.run_all [--days N] [--no-collect]` esegue
`collect -> clean -> entities -> dedup -> score -> export_dashboard` in ordine, stampa i conteggi
di ogni stadio e **si ferma** al primo che produce zero item (invece di continuare con numeri
falsi, il rischio che il task segnalava). `entities` rigenera `config/entities.yaml` da
`dashboard-config.js` PRIMA di `dedup`, che ne dipende (filtro di rilevanza + matching entita' nel
clustering) — l'ordine che in passato andava ricordato a mano.
`run_retry.bat`/`rerun_retry.bat` esistenti sono stati verificati: sono il retry delle annotazioni
DeepSeek del golden set (`data/golden/retry_deepseek.py`), non questa pipeline — non la coprono,
serviva uno script nuovo.

## Cosa questa beta NON fa (dichiarato, non nascosto)

- **Le IJ non sono verificate**: `territory_ij` resta sempre `null`, mai dedotto (`PROJECT_AUDIT.md`
  §D.3).
- **I campi di giudizio** (`risk`, `opportunity`, `wedge`, `signal_to_vrh`, `signal_to_media`,
  `owner`, `deadline`, ...) restano ai default: sono a cura umana, il pilot non li inventa.
- **`novelty` non e' implementata**: tolta dal punteggio in C3 (non solo lasciata a `None`),
  richiede una baseline storica a 30gg che oggi ha una sola fonte su 17 (RS_ENT_001/RTRS, e nemmeno
  quella e' cresciuta col backfill di C4).
- **`signal_score` ordina su 22 gradini, non 50+**: e' il tetto reale dei segnali osservabili su un
  corpus di media locali di questa forma (82% singoletti), non un difetto di calibrazione — vedi
  sopra.
- **`velocity` e' un flag, non piu' una componente continua** (`trending_now`): solo una minoranza
  dei cluster ha mai 2 articoli in 4h, un tetto strutturale del corpus (RFC §5.3), non del codice.
- **9 card di `dashboard-config.js`** (finansiranje, doboj, predsjednistvo, banjaluka, sps,
  sp-demos, dns-nps, josic, obren) non hanno ancora codici `modules` dichiarati: C0b, decisione
  frontend card-per-card, esplicitamente fuori dallo scope pilot di questa sessione
  (`HANDOFF_PROGRESS.md` §5: `dashboard-config.js` si legge, non si modifica senza una decisione
  dedicata).
- **BL_IJ3_006 (Banjaluka24) resta contaminata**: bug di estrazione (`trafilatura` incolla testo di
  articoli correlati, 71,4% degli item di quella fonte) misurato ma non corretto — rischio noto sul
  clustering di quella fonte specifica, non su tutto il corpus.
- **Il backfill C4 e' parziale**: 4 fonti su 5 troncate da `MAX_BACKFILL_URLS=100` (altra storia
  disponibile, non ancora raccolta), RS_ENT_001 (RTRS) ferma a 2 giorni. Mediana fonti attive/
  giorno 5,5, sotto il bersaglio di 8 dichiarato dal task.
- **Metriche di FIX_01 non rimisurate** sul corpus nuovo (`is_political`, precisione entita',
  precisione clustering su un campione umano) — richiederebbe un nuovo giro di annotazione LLM, non
  fatto in questa sessione per costo/tempo. Le soglie di C2 sono comunque calibrate con F1 misurati
  indipendentemente sul corpus corrente.
