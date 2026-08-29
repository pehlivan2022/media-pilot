# B3 RESULTS — TASK_BETA_01 (B3.1 estensione golden set + B3.2 ricalibrazione soglie)
Date: 2026-08-28

## SUPERATO da TASK_BETA_02 C1 (stesso giorno, sessione successiva)

La calibrazione B3.2 sotto (Jaccard su n-grammi) è stata sostituita: `pilot/dedup.py` ora usa
TF-IDF+coseno per la prova di corpo, sia in dedup che in clustering. `body_overlap_threshold`/
`body_similarity_threshold` in `config/scoring.yaml` portano valori nuovi, calibrati sulla nuova
metrica — 0.20/0.80 su coseno, non 0.20/0.50 su Jaccard. Vedi `docs/TASK_BETA_02_RESULTS.md` §C1
per i numeri correnti. Questo file resta come registrazione storica di B3.1 (estensione golden
set — quella resta valida) e di cosa era vero con Jaccard quel giorno.

## B3.1 — Estensione golden set

Corpus nuovo (`clean.jsonl`, 1528 item post-B1) analizzato con `generate_candidate_pairs()`
(finestra 72h, soglia blocking 0.35): **42 coppie dup-like (≥0.90), 1298 event-like (0.35-0.90)**,
contro le 8 totali della prima run FIX_00. Batch scelto con l'utente ("piccolo mirato"): tutte le
41 dup-like nuove (una era già coperta dal golden originale) + campione di 40 event-like + 30
negative sotto soglia = **111 coppie**, giudicate da Anthropic+DeepSeek.

Tooling: `pilot/golden/b3.py`, nuovo script — non tocca `sample.py`/`pairs.py`/`review.py`/
`build.py` (vincolo FIX_00 "nessuno di questi file va riscritto"): riusa le loro funzioni pure e
punta a `data/golden_b3/` con un monkeypatch a runtime dei `Path` di modulo, non con modifiche ai
file. Revisione umana fatta dall'utente su `http://localhost:8766` (porta diversa da 8765
originale).

**Risultati**: accordo A/B **98.2%** (109/111), solo 2 disaccordi, entrambi risolti a favore di
Anthropic (DUPLICATO). Spotcheck: 54/109 accordi controllati.

**Nota sul controllo campione**: la coda spotcheck usa il tasto SPAZIO per "confermato", 1/2 per
scegliere fra due etichette diverse — ma nella coda spotcheck le due etichette sono per
costruzione identiche (i modelli erano già d'accordo), quindi 1/2 e spazio producono lo stesso
esito visibile con semantica di salvataggio diversa. L'utente ha usato 1/2 pensando "confermo"
(confermato esplicitamente). Corretto in `data/golden_b3/decisions.jsonl` (23 righe passate da
`A`/`B` a `CONFIRMED`, backup in `decisions.jsonl.bak-before-confirmed-fix`). **Di conseguenza
`errori_trovati_nel_controllo: 0/54` non è una misura indipendente della qualità dell'accordo — è
0 per costruzione dopo la correzione, non perché il controllo abbia verificato 54 casi e trovato
zero errori.** La soglia 10% di FIX_00 non è stata testata in questo giro.

**Trappola nell'interfaccia, non corretta** (file riservato): `review.html:158-164` lega i tasti
1/2 a "scegli A/scegli B" in ENTRAMBE le code, ma solo SPAZIO conta come "confermato" nella coda
spotcheck — la prossima persona che revisiona rischia lo stesso errore. Segnalato, non corretto
(vincolo "nessuno di questi file va riscritto" da FIX_00).

`data/golden_b3/golden_dataset.json`: 111 coppie, `items: []` (questa estensione copre solo
coppie, non annotazioni item-level — non richiesto da B3.1).

---

## B3.2 — Ricalibrazione soglie

Campione combinato: golden originale (58 coppie) + golden_b3 (111 coppie) = **169 coppie**, **162
utilizzabili** (7 scartate: label SKIPPED/OTHER o item mancante in `clean.jsonl`). Distribuzione:
**44 DUPLICATO, 7 STESSO_EVENTO, 111 DIVERSI**.

### Scoperta non pianificata: bug di estrazione su BL_IJ3_006 (Banjaluka24)

Il primo giro di calibrazione (162 coppie, tutte le fonti) mostrava una cosa impossibile per una
soglia pulita: precisione che **peggiora** salendo da 0.35 a 0.50 (0.583→0.566), con DIVERSI che
arrivava fino a **0.83** di Jaccard sul corpo — dentro il range DUPLICATO (0.41-1.0). Indagato:
**tutte e 33** le coppie DIVERSI con Jaccard >0.50 erano dalla stessa fonte, `BL_IJ3_006`
(Banjaluka24), media Jaccard 0.612 solo per quelle — contro <0.02 di media per lo stesso confronto
su ogni altra fonte del corpus.

Causa verificata leggendo il testo grezzo: `trafilatura`, su questa fonte, estrae **il testo
completo di 2-3 articoli correlati** più una lista teaser ("Politika2 dana ago...") insieme
all'articolo richiesto — non è markup residuo (tagliare le prime righe non cambia il punteggio,
testato: 0.830→0.842), è contenuto vero di altri articoli incollato in coda. **100/140 item di
questa fonte in `clean.jsonl` (71.4%) ne sono affetti.**

**Non corretto in questa sessione** — stesso trattamento della contaminazione temporale di B1:
è un bug di estrazione specifico di una fonte, non una soglia. Marcato per dopo. Effetto pratico
oltre alla calibrazione: qualunque cosa legga `text` per BL_IJ3_006 (relevance filter, entity
matching, clustering, score) lavora oggi anche sul testo di articoli non pertinenti incollato in
coda — non solo la calibrazione ne risente.

### Soglie aggiornate in `config/scoring.yaml`

Tutte ricalibrate **escludendo le 52 coppie che coinvolgono BL_IJ3_006** (rimangono 110: 40
DUPLICATO, 7 STESSO_EVENTO, 63 DIVERSI) — sul campione pulito la separazione è quasi netta:
**DIVERSI max 0.4136, DUPLICATO min 0.4072.**

| soglia | prima | dopo | n | evidenza |
|---|---|---|---|---|
| `dedup.body_similarity_threshold` | 0.50 (a occhio, n=5+3) | **0.50 (confermato)** | 40 dup / 63 div | prec 1.0, rec 0.975, F1 0.987 — il massimo misurato |
| `clustering.body_overlap_threshold` | 0.50 | **0.20** | 45 pos / 63 div | prec 0.978, rec 0.957, F1 0.968 (0.50 dava F1 0.907, perdeva 8% dei positivi) |
| `clustering.window_hours` | 60 (mai calibrata) | **60 (confermato)** | 51 positivi | nessun positivo oltre 32.34h; **censura nota**: `generate_candidate_pairs` campiona solo entro 72h |
| `clustering.max_document_frequency` | 0.10 (n=1 corpus) | **0.10 (non toccato)** | 520 item rilevanti | il gap che lo giustificava è sparito, vedi sotto — decisione di prodotto, non presa qui |

### `max_document_frequency` — il gap non c'è più

Document frequency delle entity-key su 520 item rilevanti (era: dodik 28.1%, minic 15.7%, poi
stanivukovic 7.6% → gap netto):

```
ij5-konkurencija  50.2%   finansiranje    28.3%   doboj            23.7%   predsjednik-rs  21.2%
dodik             37.7%   us-snsd         27.5%   izborni-proces   22.7%   stanivukovic    15.8%
                          snsd            27.1%   cik              22.7%   minic           15.4%
                                                                            predsjednistvo  15.4%
```

Continuum, non gap: a 0.10 il filtro escluderebbe **~11 entità** dal segnale di clustering (prima
ne escludeva 2 — dodik, minic). Cambio di comportamento non richiesto, non applicato. Nota di
merito ulteriore: `ij5-konkurencija`/`doboj`/`predsjednik-rs`/`izborni-proces`/`cik` sono
categorie/ruoli/luoghi, non attori — una soglia DF unica su tutte le entità sta facendo un lavoro
che forse dovrebbe fare il tipo di entità (`config/entities.yaml` distingue già `actor`/`party`/
altri tipi). Decisione di prodotto per l'utente, non presa qui.

### Altri numeri utili non tradotti in soglie

- `coppie_sotto_soglia_risultate_positive`: 2 su 30 campionate sotto la soglia di blocking 0.35 —
  vero recall perso dal blocking stesso (non dalle soglie di dedup/clustering), coerente col fatto
  che il blocking a 0.35 è deliberatamente più basso delle soglie reali.
- `signal_weights.*` e `velocity.max_items_per_group`: **non toccati**, restano `# da calibrare`.
  Fuori dall'ordine esplicito di B3.2 (dedup → clustering.body_overlap → window_hours →
  max_document_frequency); calibrarli richiede un metodo diverso (non sono soglie binarie su una
  feature, sono pesi di uno score composito) — non improvvisato qui.

---

## Cosa resta aperto, per l'utente

Due contaminazioni "marcate per dopo" nella stessa sessione, entrambe con causa nota e quantificata
ma non corrette:
1. **B1 §5** — date `published_at` false da pagine sitemap non-articolo (32/1284 item, 3 fonti).
2. **B3.2** — testo contaminato da articoli correlati incollati su BL_IJ3_006 (100/140 item, 71.4%
   di quella fonte).

Nessuna delle due è stata corretta: sono decisioni di prodotto (quale delle risposte possibili
adottare), non misure. Il B3.2 di questa sessione è stato calibrato **escludendo** la fonte
contaminata dal campione di calibrazione, non correggendo il bug — le soglie sopra sono valide per
le altre 16 fonti; per BL_IJ3_006 il segnale di body-similarity resta inaffidabile finché
l'estrazione non è corretta.
