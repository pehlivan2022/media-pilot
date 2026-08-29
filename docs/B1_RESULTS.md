# B1 RESULTS — TASK_BETA_01
Date: 2026-08-28

## AGGIORNAMENTO — la contaminazione §5 è stata corretta (non da questa sessione)

Durante B3, una **sessione parallela** ha aggiunto un filtro `out_of_window()` in `pilot/clean.py`
(commit-like, non Git: solo mtime, 05:22) che scarta in `clean()` gli item con `published_at` fuori
da `BACKFILL_DAYS_DEFAULT ± 1gg` rispetto a `scraped_at`, tenendo gli item senza data (regola "zero
invenzione"). Risolve esattamente la contaminazione descritta in §5 sotto — stessa causa, stessa
diagnosi, fix diverso da quelli che avevo elencato come opzioni. **Non l'ho scritto io, l'ho
integrato**: rigenerata la pipeline (`clean`→`dedup`→`score`) sul nuovo `clean.jsonl` (1488, non
più 1528) e RIMISURATO tutto. Risultato:

- `window_actual_days` di corpus: **30** (era 56) — ora combacia esattamente con
  `BACKFILL_DAYS_DEFAULT`, niente più range 1996→2026.
- `velocity`: **4 valori distinti** (0.0, 1.0, 2.0, 3.0) — soddisfa il criterio B0 ("più di 2
  valori"), che con la contaminazione attiva NON era soddisfatto.
- singoletti: **83.2%** (318/382 cluster) — meglio dell'84% di riferimento pre-B1/B2 in
  `TASK_BETA_01.md`. **Nota**: questo numero riflette ANCHE `clustering.body_overlap_threshold`
  abbassato da 0.50 a 0.20 in B3.2 (vedi `docs/B3_RESULTS.md`) — i due effetti (fix contaminazione
  + soglia clustering più permissiva) sono cumulati in questa run, non isolati l'uno dall'altro.
- bucket 4h e giorno dominante (§2/§3 sotto): **invariati, 55.0% e 45.1%** — il fix scarta solo 40
  item su 1488 (2.7%), non sposta la concentrazione del corpus sull'ultimo giorno.

**Verdetto aggiornato**: bucket 4h e giorno dominante restano FAIL. Ma la tripla decisiva di "LA
COSA PIÙ IMPORTANTE" ora è **2 su 3 soddisfatta** (velocity sì, source_diversity sì, novelty no —
per costruzione, `score.py:193`), contro 0 su 3 nella misura originale sotto contaminazione. Il
resto di questo file (§0-§7) è la misura ORIGINALE, prima del fix — lasciata intatta come
registrazione di cosa è stato misurato e quando; i numeri aggiornati sono qui sopra e in
`docs/HANDOFF_PROGRESS.md` §7.

---

## Verdetto in una riga (misura originale, sotto contaminazione — vedi aggiornamento sopra)

**FAIL su tutti e tre i criteri di B1**, e la tripla di "LA COSA PIÙ IMPORTANTE" (velocity, novelty,
source_diversity) è **invariata o peggiorata**, non migliorata, rispetto ai numeri registrati nella
tabella STATO di `TASK_BETA_01.md`. La pipeline (`clean`→`dedup`→`score`) era disallineata rispetto
all'ultimo raw scritto dal collect (vedi §0) ed è stata rigenerata prima di misurare.

## 0. Input verificato

- collect 30gg: completed / exit 0 (confermato dall'handoff)
- `data/raw/*.jsonl`: 2 file, **1627 record totali**, **17 fonti distinte** (non 18: GDELT/Google
  News restano NON_PASSA, non sono fonti di raccolta)
- min `published_at` nel raw: `1996-01-01` — **non valido, vedi §5 Contaminazione**
- max `published_at` nel raw: `2026-08-27T23:25:47Z`
- **Pipeline rigenerata in questa sessione** perché `data/raw/2026-08-28.jsonl` (mtime 02:28) era
  più recente di `data/clean.jsonl`/`items.jsonl`/`clusters.jsonl`/`scored_*` (mtime 01:15–01:46):
  il run di collect ha continuato a scrivere dopo l'ultima pipeline eseguita. Rilanciati in ordine
  `python -m pilot.clean` → `python -m pilot.dedup` → `python -m pilot.score`. Non toccato
  `pilot/score.py` né `config/entities.yaml`.
  - `clean`: raw 1627 → puliti 1528 (99 EMPTY_CONTENT)
  - `dedup`: puliti 1528 → dopo dedup 1284 → rilevanti (`is_relevant`) 532, scartati 752 (58%)
  - `score`: 532 item rilevanti → 501 cluster

## 1. `window_actual_days` (per fonte, da `config/sources.yaml`)

Già scritto dal collect completato (`write_window_actual_days`); ricalcolato con
`compute_window_actual_days()` e **coincide esattamente** — nessuna scrittura necessaria.

| source_id | days |
|---|---:|
| BIH_ELEC_002 | 16 |
| POL_RS_001 | 10 |
| RS_ENT_001 | 2 |
| BIH_ELEC_003 | 6 |
| RS_ENT_002 | 6 |
| RS_IJ_001 | 4 |
| BL_IJ3_001 | 9 |
| BL_IJ3_006 | 7 |
| RS_IJ_013 (Dobojski, wayback) | 2 |
| RS_IJ_012 | 3 |
| BL_IJ3_002 (Nezavisne) | **34** |
| BL_IJ3_003 (Glas Srpske) | 1 |
| BL_IJ3_007 (BL Portal) | 9 |
| RS_IJ_014 (RTV Doboj) | 7 |
| RS_IJ_018 (InfoBijeljina) | 0 |
| SRC_009 (N1 BiH) | 1 |
| FBIH_001 (Klix) | 1 |
| ECO_001 (Capital.ba, wayback) | 20 |

**Nota**: alcuni valori (BIH_ELEC_002=34, ECO_001=20, BL_IJ3_002=34) sono gonfiati da date
`published_at` errate ereditate dal `lastmod` di pagine sitemap non-articolo (vedi §5). Il numero
è calcolato correttamente dal codice esistente (non toccato), ma l'input non è pulito.

## 2. Copertura bucket 4h

**Livello dichiarato**: `items.jsonl` (1284, tutti gli item deduplicati, rilevanti e non — è la
stessa popolazione che `pilot/score.py:compute_layer1_and_signal` usa internamente per
`window_actual_days`/`velocity_baseline_4h`). I numeri di riferimento in `TASK_BETA_01.md`
("28/48 = 58%") sommano a 784, cioè livello `clean.jsonl` di allora: ricontrollato anche a quel
livello sul corpus attuale (`clean.jsonl`, 1528, stessa finestra 30gg) e il risultato è identico
al bucket %, quindi il verdetto **non dipende dal livello scelto**.

**Finestra usata**: gli ultimi 30 giorni civili da `max(published_at)`, ancorati a
`BACKFILL_DAYS_DEFAULT = 30` in `pilot/collect.py:24` (il parametro del collector stesso, non una
soglia scelta per far tornare il numero). Il full-range grezzo (1996→2026) non è una finestra
sensata, vedi §5.

| | bucket attesi | bucket non vuoti | copertura | target | esito |
|---|---:|---:|---:|---|---|
| oggi (da TASK, livello clean, 7gg span) | 48 | 28 | 58% | ≥70% | riferimento storico |
| **items.jsonl, 30gg** | **180** | **99** | **55.0%** | ≥70% | **FAIL** |
| clean.jsonl, 30gg (cross-check livello) | 180 | 99 | 55.0% | ≥70% | FAIL (stesso risultato) |

**Direzione**: 58% → 55%, leggermente peggio, non meglio — nonostante 3.5× più item, perché la
finestra si è allargata ~4× mentre il volume resta concentrato negli ultimi 2 giorni (vedi §3).

## 3. Distribuzione per giorno

| | giorno dominante | item | totale | quota | target | esito |
|---|---|---:|---:|---:|---|---|
| oggi (da TASK) | 08-27 | 479 | 784 | 61% | ≤25% | riferimento storico |
| **items.jsonl, 30gg** | **2026-08-27** | **565** | **1252** | **45.1%** | ≤25% | **FAIL** |
| clean.jsonl, 30gg (cross-check) | 2026-08-27 | 728 | 1488 | 48.9% | ≤25% | FAIL |

**Direzione**: 61% → 45%, miglioramento reale (16 punti), ma resta ben sopra la soglia del 25%.
Il corpus resta piegato sull'ultimo giorno di raccolta.

## 4. Distribuzione cluster

| cluster_size | count |
|---:|---:|
| 1 | 480 |
| 2 | 18 |
| 4 | 1 |
| 5 | 1 |
| 7 | 1 |

- cluster totali: 501
- item clusterizzati: 532
- dimensione massima: 7
- **singoletti: 480/501 = 95.8%** — peggio dell'84% registrato nella tabella STATO di
  `TASK_BETA_01.md` prima di B0/B1.

## 5. Contaminazione temporale — trovata durante questa verifica, non nel task originale

32 item su 1284 in `items.jsonl` (2.5%) hanno `published_at` **fuori dalla finestra dei 30 giorni**
del collect, con date da `1996-01-01` a metà luglio 2026. Non sono notizie vecchie: sono pagine
non-articolo raccolte via sitemap che riportano il `lastmod` della pagina, non una data di
pubblicazione:

- `BIH_ELEC_002` (podlupom.org): endpoint `wp-json/contact-form-7/...` (1996-01-01, chiaramente un
  default/epoch), pagine statiche istituzionali (`izbori-u-bih/`, `press-kutak/pr-kontakt/`, ecc.)
- `BL_IJ3_002` (Nezavisne): sezione `automobili/auto-novosti` — recensioni auto 2019-2026, fuori
  tema politico e fuori finestra
- `ECO_001` (Capital.ba, via Wayback): pagine `najava-dogadjaja-per-...` (agenda eventi) con date
  sparse 2023-2026

Effetto misurato: se si prende il range grezzo (min→max reale, 1996→2026) come finestra per il
bucket 4h, si ottengono **67.182 bucket attesi, 125 non vuoti, 0.2%** — non è una lettura di B1,
è la prova quantitativa della contaminazione. Escluso da §2/§3 apposta (non è la finestra che B1
intende misurare).

**Effetto più serio**: `window_actual_days` a livello di corpus (usato da
`compute_layer1_and_signal` per `velocity_baseline_4h`) è **56** — anche questo gonfiato dalla
stessa contaminazione, non un vero 30gg pulito. Con una finestra così ampia e quasi tutta vuota,
la mediana dei bucket collassa a 0, e con `max(baseline_4h, 1)` il denominatore si blocca a **1**:
`velocity` smette di essere una velocità normalizzata e diventa semplicemente il conteggio grezzo
di articoli nelle ultime 4h.

**Non corretto in questa sessione.** Toccare `collect.py`/`clean.py` per filtrare queste date è
una decisione di prodotto (tre risposte diverse possibili: scartare l'item, azzerare
`published_at` a `null`, o escludere i pattern URL non-articolo per fonte), non una misura — vedi
regola 6. Segnalato qui, non corretto qui.

## 6. Baseline / novelty

- `window_actual_days` (corpus, da `measured`): **56** — vedi §5, non affidabile
- `baseline_incomplete`: **False** su 501/501 cluster (soglia `<3` giorni, banalmente vera con un
  range gonfiato a 56)
- `velocity_baseline_4h` (corpus): **1** — collassato, vedi §5
- cluster con `velocity is None`: **0/501**
- cluster con `novelty is None`: **501/501 — sempre, per costruzione.** `pilot/score.py:193`
  assegna `novelty = None` in modo incondizionato (commento: "richiede un corpus storico di 30gg
  che questo pilot non accumula ancora"). Non è un effetto della finestra di B1: la metrica non è
  implementata, indipendentemente da quanti giorni di storia ci siano. Non toccato (fuori scope,
  `score.py` riservato).

### La tripla decisiva (da "LA COSA PIÙ IMPORTANTE" di TASK_BETA_01.md)

| segnale | prima (da TASK STATO) | dopo (misurato ora) | direzione |
|---|---|---|---|
| `velocity`, valori distinti | 3 (0.0: 140, 0.5: 25, 1.0: 1) | **2** (0.0: 476, 1.0: 25) | **peggio** — sotto la soglia B0 ("più di 2 valori") |
| `novelty` | None su 150/150 | None su 501/501 | invariato, per costruzione (§6) |
| `source_diversity = 1` (singoletti) | 84% | **95.8%** | **peggio** |

**Nessuna delle tre condizioni de "LA COSA PIÙ IMPORTANTE" è soddisfatta.** Secondo il criterio che
il task stesso pone come decisivo, l'allargamento a 30gg/17 fonti **non ha ancora riacceso il
ranking**: `velocity` ha addirittura perso un valore (il denominatore collassato di §5 ne è la
causa più probabile), e i singoletti sono aumentati, non diminuiti — coerente con B2 (nuove fonti)
non ancora fatto.

## 7. Verdetto B1

**FAIL** su tutti e tre i "done quando" della sezione B1:
- bucket 4h ≥70%: **55.0%** — FAIL (era 58%, leggermente peggio)
- giorno dominante ≤25%: **45.1%** — FAIL (era 61%, migliorato ma non abbastanza)
- novelty non più None: **ancora None su 501/501** — FAIL, per costruzione (§6), non per finestra insufficiente

## Note

Solo fatti misurati. Nessuna soglia toccata, nessun file fuori scope modificato.

**ponytail: contaminazione temporale (§5) rimandata a dopo B3, decisione utente 2026-08-28.**
Non corretta ora (scartare item / azzerare `published_at` / filtrare pattern URL non-articolo —
tre risposte diverse, decisione di prodotto). Effetto noto e accettato: `velocity`/`novelty` di
corpus restano su una baseline degenere finché non si chiude questo punto; B3 procede comunque su
richiesta esplicita dell'utente, quindi le soglie ricalibrate in B3 andranno **ricontrollate**
dopo la correzione della contaminazione, non considerate definitive.

---

## 8. CORREZIONE MISURATA — 2026-08-28, sessione di verifica

Tre affermazioni causali di questo documento sono state ricontrollate sui file. Due sono false.

### 8.1 La contaminazione NON collassa `baseline_4h` (§5 è sbagliata)

Ricalcolo della baseline sulla sola finestra pulita (30gg da `max(published_at)`, i 26 item fuori
finestra esclusi), stessa formula di `score.py:_bucket_4h` + bucket vuoti:

| | bucket attesi | non vuoti | mediana | `baseline_4h` |
|---|---:|---:|---:|---:|
| corpus attuale (contaminato) | 67.182 | 125 | 0 | `max(0,1)` = **1** |
| corpus pulito (30gg) | 186 | 100 (53.8%) | 1 | `max(1,1)` = **1** |

**Identico.** Il denominatore è 1 perché il corpus è genuinamente rado (mediana 1 articolo per
bucket da 4h), non per la contaminazione. Correggere le date **non muove `velocity` di un valore**.

Ambito reale della contaminazione, delimitato: sporca `window_actual_days` (56 invece di 31) e i
valori per fonte scritti in `config/sources.yaml`. **Non** tocca `velocity`, `baseline_4h`, né
`baseline_incomplete` (≥3 in entrambi i casi). È un problema di onestà del dato, non di segnale.

**Conseguenza operativa: B3 non era bloccato.** Il vincolo dichiarato in `HANDOFF_PROGRESS.md` §6.7
("B3 non può partire finché la contaminazione non è decisa") non esiste.

### 8.2 La causa vera di `velocity` a 2 valori: densità, non finestra né denominatore

Articoli per cluster nella **migliore** finestra da 4h (non solo l'ultima del corpus), su 501 cluster:

| max articoli in 4h | cluster |
|---:|---:|
| 1 | 493 |
| 2 | 5 |
| 3 | 2 |
| 4 | 1 |

**8 cluster su 501 (1.6%) hanno mai due articoli entro 4 ore.** Con qualunque baseline e qualunque
ancoraggio, `velocity` non può assumere più di una manciata di valori. Allargare la finestra di
`velocity` non aiuta: solo 21 cluster su 501 hanno ≥2 item *in assoluto*.

### 8.3 Il salto dei singoletti 84% → 95.8% NON è causato dal filtro DF di B4a

Riclusterizzazione offline degli stessi 532 item rilevanti (`pilot.dedup.cluster`, nessun file
modificato), variando solo `clustering.max_document_frequency`:

| configurazione | cluster | singoletti | cluster max |
|---|---:|---:|---:|
| DF 0.10 (attuale) | 501 | 480 (95.8%) | 7 |
| DF disattivato | 419 | 397 (**94.7%**) | **63** |
| DF 0.35 | 459 | 436 (95.0%) | 41 |
| ultimi 7gg, DF 0.10 | 244 | 228 (**93.4%**) | 7 |
| ultimi 7gg, DF off | 227 | 212 (93.4%) | 18 |

Due letture:
- **Il filtro DF di B4a costa ~1 punto di singoletti e va tenuto**: spegnerlo riapre il collasso che
  B4a ha chiuso (cluster da **63** item). La ricalibrazione di B3 su `max_document_frequency` resta
  utile ma non è urgente né è la leva sui singoletti.
- **Nemmeno la finestra a 30gg è la causa**: sugli ultimi 7 giorni i singoletti sono 93.4%. Il tasso
  è 93–96% in *ogni* configurazione provata. Il confronto con l'84% storico non è omogeneo (corpus,
  filtro di rilevanza e clustering sono tutti cambiati) e non va usato come regressione.

**Il collo di bottiglia è la sovrapposizione fra fonti**: le 17 fonti raramente coprono lo stesso
evento, e il dedup ha già fuso le ripubblicazioni identiche. È esattamente il bersaglio di **B2**,
non di B1 né di B3.

---

## 9. Filtro temporale APPLICATO — 2026-08-28

Decisione presa (utente + due seconde opinioni esterne): scartare gli item con `published_at` fuori
dalla finestra di raccolta, **nel clean**. Implementato in `pilot/clean.py` (`out_of_window`,
`STALE_DAYS = 30`, tolleranza ±1 giorno; gli item **senza** data si tengono — dato mancante non è
dato sbagliato) e riusato in `collect.py:compute_window_actual_days`, che legge `data/raw` e senza
il guard avrebbe continuato a scrivere valori gonfiati in `config/sources.yaml`.

Scartati: **40 item su 1627 al livello raw** (26 sopravvivevano al dedup), da 4 fonti —
`ECO_001` 10, `BIH_ELEC_002` 8, `BL_IJ3_002` 6, `BL_IJ3_007` 2.

### Cosa è cambiato — pipeline rilanciata `clean → dedup → score`

| | prima | dopo |
|---|---:|---:|
| `window_actual_days` (corpus) | 56 | **30** ✔ |
| `window_actual_days` in `sources.yaml` | BL_IJ3_002 34, ECO_001 20, BIH_ELEC_002 16, BL_IJ3_007 9 | **27 / 9 / 5 / 7** ✔ |
| span date del corpus | 1996-01-01 → 2026-08-27 | **2026-07-29 → 2026-08-27** ✔ |
| item puliti | 1528 | 1488 |
| cluster | 501 | 489 |
| test | 19/19 | **19/19** |

### Cosa NON è cambiato — i tre criteri di B1

| criterio | target | prima | dopo | esito |
|---|---|---:|---:|---|
| bucket 4h non vuoti | ≥70% | 55.0% | **55.0%** | FAIL, **identico** |
| giorno dominante | ≤25% | 45.1% | **45.1%** | FAIL, **identico** |
| `novelty` non `None` | — | None 501/501 | **None 489/489** | FAIL, per costruzione |
| `velocity_baseline_4h` | — | 1 | **1** | invariato |
| `velocity`, valori distinti | >2 | 2 (0.0/1.0) | **2 (0.0/1.0)** | invariato |
| singoletti | — | 95.8% | **95.7%** | invariato |
| `signal_score`, valori distinti | — | 16 | **16** | invariato |

**Conferma empirica di §8.1.** La contaminazione era un problema di onestà del metadato, non una
causa del ranking piatto: correggerla sistema `window_actual_days` e `sources.yaml` e **non muove
nessuno dei tre criteri di B1, né un solo valore di `velocity`**. La catena causale scritta in §5
("la contaminazione collassa il denominatore → velocity muore") è ora smentita due volte: per
ricalcolo (§8.1) e per esecuzione (qui).

**Quello che resta da fare è in `docs/RFC_SECONDA_OPINIONE_02.md`**: la causa misurata del ranking
piatto è `clustering.body_overlap_threshold: 0.50`, che su 16 coppie cross-fonte a titolo quasi
identico (stesso evento certo) non scatta **mai** — Jaccard corpo 0.184–0.374, mediana 0.245.

File toccati: `pilot/clean.py`, `pilot/collect.py`, `config/sources.yaml` (solo le 4 righe
`window_actual_days` sbagliate, per sostituzione mirata). `score.py`, `config/scoring.yaml`,
`config/entities.yaml`, frontend: **non toccati**.
