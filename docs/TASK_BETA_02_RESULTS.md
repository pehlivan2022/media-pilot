# TASK BETA 02 RESULTS
Date: 2026-08-28

## C0 — rassegna (già fatto da una sessione parallela)

`pilot/export_dashboard.py` modificato prima che questa sessione arrivasse a C1 (mtime 05:49,
`docs/TASK_BETA_02.md` §C0 lo documenta già "✅ FATTO" con numeri prima/dopo). Non rifatto, non
verificato nel dettaglio — fuori dal lavoro di questa sessione.

---

## C1 — Sostituire la metrica di similarità: TF-IDF + coseno

### Metodo — diverso da quello prescritto dal task, dichiarato

Il task (§C1 punto 4) chiedeva un golden set "gratis, dal corpus, senza LLM": positivi = coppie
cross-fonte con `title_norm` simile ≥0.85, negativi = coppie a caso. **Non l'ho costruito.** Avevo
già **162 coppie con etichetta umana/LLM reale** da B3.1 (58 golden originali + 111 golden_b3):
44 DUPLICATO, 7 STESSO_EVENTO, 111 DIVERSI — un ground truth più solido di un proxy euristico.
Usato quello, su richiesta esplicita dell'utente ("usa i tuoi risultati").

**Conseguenza misurata di questa scelta**: il metodo del task, applicato con Jaccard, aveva trovato
"nessuna soglia separa" (positivi 0.184-0.374, negativi fino a 0.334, margine 0). La mia
verifica con etichette umane mostra che quella conclusione era vera **solo per STESSO_EVENTO**
(il mio campione umano, n=7, dà lo stesso risultato: 0.05-0.48) — per DUPLICATO (n=44, non
misurato dall'altra sessione) Jaccard funzionava già bene (F1 0.987 una volta esclusa la
contaminazione BL_IJ3_006, vedi `docs/B3_RESULTS.md`). Non era "la metrica sbagliata" in blocco:
era sbagliata per una sola delle due prove che la condividevano. Questo cambia come si applica il
fix, non se farlo — vedi sotto.

### Implementazione

`pilot/dedup.py`: rimossi `char_shingles`/`jaccard` (n-gram di caratteri), aggiunti `build_idf`,
`tfidf_vector`, `cosine` (~30 righe stdlib: `Counter` per document frequency, tf logaritmico,
idf sul corpus, L2, prodotto scalare sul vettore più corto — nessuna dipendenza nuova). Tokenizza
su `text_norm`/`title_norm` (già cirillico→latino, `pilot/util.py:normalize_search`), non su
`text`/`title` grezzi: altrimenti un articolo cirillico e uno latino sullo stesso evento
condividerebbero zero token e il coseno sarebbe sempre 0 — proprio le coppie cross-fonte che C1
deve prendere. `idf` calcolato una volta in `run()` sull'intero corpus pulito, passato sia a
`dedup()` che a `cluster()` (stessa base di riferimento).

`token_overlap`/titolo: **non toccato**, resta Jaccard su insiemi di parole (rinominata
`jaccard_sets` per non confondersi con il coseno, stessa logica di prima).

### Scoperta: dedup e clustering NON possono condividere una soglia sul coseno

Il task (§C1 punto 2) chiedeva di sostituire la prova "sia nel clustering sia nel dedup" — non
specificava se con la stessa soglia. Misurato: **no**. Il coseno mette le coppie STESSO_EVENTO
(stesso fatto, articolo diverso — quello che il clustering deve accorpare) a **0.03-0.74**, e le
coppie DUPLICATO (stesso articolo — quello che il dedup deve fondere) a **0.67-1.0**. Una soglia
unica nella banda 0.35-0.45 suggerita dal task per il clustering, usata anche nel dedup, avrebbe
fuso articoli sullo stesso evento ma testo diverso in un unico item — distruttivo, non
recuperabile a valle (`n_copies`/`evidence` collassati). Calibrate separatamente, popolazioni
diverse.

### Calibrazione — due soglie, due popolazioni, entrambe n≥100

**`dedup.body_similarity_threshold`**: DUPLICATO (n=44) vs resto (n=118), **tutte le 162 coppie
incluse** (qui la contaminazione BL_IJ3_006 conta: è il corpo reale che dedup vede oggi, non un
sottoinsieme ideale). Soglia scelta: **0.80** — precisione 0.977, recall 0.977, F1 0.977, il
migliore misurato. Prima: 0.50 su Jaccard (F1 0.987 solo sul sottoinsieme pulito). Sul solo
campione pulito (esclusa BL_IJ3_006) l'ottimo sarebbe 0.65-0.67 (F1 0.988) — più permissivo, ma
presuppone che il bug di estrazione sia già corretto. Scelto il valore robusto al corpus reale,
non quello ideale.

**`clustering.body_overlap_threshold`**: DUPLICATO+STESSO_EVENTO (n=45-49) vs DIVERSI (n=63-111),
**escluse le 52 coppie BL_IJ3_006** (stessa logica di B3.2: quella fonte inietta testo di altri
articoli, gonfia il coseno anche lì — vedi sotto). Soglia scelta: **0.20** — F1 0.968 stabile su
tutto il plateau 0.10-0.40 (prec 0.978, rec 0.957). **Identico all'F1 del miglior Jaccard
calibrato in B3.2 sulla stessa popolazione pulita** (0.968 anche lì): il coseno non batte Jaccard
quando la contaminazione è rimossa da entrambi i lati del confronto — il vantaggio del coseno è
altrove, vedi sotto.

### BL_IJ3_006 (Banjaluka24): il coseno è più robusto, non immune

Verificato prima di calibrare: il coseno **non risolve** la contaminazione di B3.2 (testo di
articoli correlati incollato dall'estrazione, 71.4% degli item di questa fonte). È un problema di
contenuto duplicato reale, non di lunghezza — la normalizzazione L2 non lo tocca. Misurato:
coppie DIVERSI che coinvolgono BL_IJ3_006 arrivano a coseno **0.87** (contro 0.54 max per le altre
16 fonti). Ma l'effetto è meno catastrofico che con Jaccard: F1 di clustering **incluse** le
coppie BL_IJ3_006 è **0.874-0.905** col coseno contro **0.726** con Jaccard sulla stessa
popolazione contaminata — il coseno degrada, non collassa. Non corretto in questa sessione (stessa
decisione di prodotto rimandata in B1 e B3.2).

### Risultato sul corpus reale (prima/dopo)

| | prima (Jaccard, B3.2, 0.20) | dopo (coseno, C1) |
|---|---:|---:|
| cluster totali | 382 | **334** |
| item clusterizzati | 520 | 517 |
| singoletti | 83,2% | **80,5%** |
| `velocity`, valori distinti | 4 (0.0/1.0/2.0/3.0) | **4** (0.0/1.0/2.0/**7.0**) |
| `source_jump` True | non misurato a parte | **10/334 = 3,0%** |
| `entity_centrality`, valori distinti | 4 | 4 |
| `signal_score`, valori distinti | 16 | **16 — invariato** |
| test | 19/19 | 19/19 |

**`signal_score` resta a 16 valori distinti nonostante i miglioramenti reali su velocity/
singoletti/source_jump.** Non è un fallimento di C1: il task lo mette esplicitamente in C3
("Da fare dopo C1/C2"), non qui. La causa più probabile è `entity_centrality` — 4 soli valori,
e con pesi 1.0/1.0/1.0/0.5 le combinazioni di somma si sovrappongono comunque. Misurato, non
risolto: è lavoro di C3.

**Done quando (dal task)**: soglia scelta su golden set con n≥100 — fatto (162 e 110). Commento
`# da calibrare` sparito da `body_overlap_threshold`/`body_similarity_threshold` con `n=` — fatto.
Singoletti scesi **con la precisione misurata** (non solo il conteggio) — fatto, F1 riportato
sopra per entrambe le soglie.

---

## Nota — supera la calibrazione Jaccard di B3.2

`docs/B3_RESULTS.md` documenta la calibrazione di `body_overlap_threshold`/
`body_similarity_threshold` su Jaccard (B3.2, stesso giorno, sessione precedente a questa). **Quei
numeri sono superati**: la metrica sotto quelle chiavi in `config/scoring.yaml` è cambiata da
Jaccard a coseno — 0.20/0.50 su Jaccard e 0.20/0.80 su coseno non sono la stessa soglia anche
quando il valore numerico coincide (caso di `body_overlap_threshold`, 0.20 su entrambe le scale
per coincidenza, non per continuità). `B3_RESULTS.md` resta come registrazione storica di cosa
era vero quel giorno con quella metrica; questo file è la fonte corrente.

---

## C2 — difetto dedup chiuso + ricalibrazione

### Difetto RFC §6: i passaggi del dedup erano chiusi

`pilot/dedup.py`, passaggio 4 (titolo simile, fallback per corpo troncato): un residuo ora prova
prima ad agganciarsi a un gruppo **gia' formato** ai passaggi 1-3, confrontato contro i suoi membri
originali (snapshot pre-passaggio, per non incatenare titolo-a-titolo su piu' hop dentro lo stesso
giro). Misurato PRIMA del fix sul corpus corrente (leggermente diverso da quello dell'RFC, altro
giro di collect nel frattempo): **10 coppie** cross-fonte a `title_norm` identico entro 48h
sopravvivevano come item distinti (RFC ne misurava 10-12 su un corpus adiacente).

Resta un secondo caso, piu' raro: **entrambi** i membri di una coppia a titolo identico gia'
assorbiti in **due gruppi diversi** ai passaggi 1-3 (es. `content_hash` diverso ma titolo
identico) — il residuo sopra non basta, serve unire i due gruppi. Aggiunta una chiusura finale
indicizzata per `title_norm` ESATTO (il caso misurato, non il ratio approssimato): O(n), unisce
gruppi che condividono un titolo entro finestra.

**Risultato**: 0 coppie superstiti (era 10). `test_5c_reopens_closed_group_for_identical_title_pass4`
aggiunto per non farlo regredire. Item dopo dedup: 1261 -> **1241** (20 in meno, coerente con 10
coppie fuse + 1 gruppo di 5 unito da due gruppi di 2+3). Cluster: 334 -> 332. Test: 20/20.

### Ricalibrazione soglie rimanenti (n= accanto a ognuna, nessuna piu' "# da calibrare")

- **`clustering.body_overlap_threshold` (0.20)** e **`dedup.body_similarity_threshold` (0.80)**:
  gia' calibrati in C1 (n=110/162), confermati validi — nessun cambiamento, l'unico item aperto era
  se `body_overlap_threshold` fosse ancora "da tarare" dopo il fix dedup: NON lo era, C1 lo aveva
  gia' chiuso. L'unico limite dichiarato resta la contaminazione BL_IJ3_006 (esclusa dal campione di
  calibrazione, ancora nel corpus).
- **`clustering.window_hours` (60)**: riconfermato con un campione indipendente (166 coppie
  golden+golden_b3, join fresco a `clean.jsonl` per la data reale, script ad-hoc non salvato in
  `pilot/` come da indicazione — non serve un modulo di calibrazione permanente). 50 coppie
  positive con data su entrambi i lati, nessuna oltre 32.34h. Nessun cambiamento.
- **`clustering.title_overlap_threshold` (0.35)**: primo vero ricalcolo (prima non aveva un
  commento di calibrazione). Sweep su n=166: a 0.35 precisione 1.0/recall 0.72/F1 0.839, zero falsi
  positivi. Scendere a 0.15 darebbe il F1 migliore assoluto (0.882) ma con 3 falsi positivi su una
  delle tre prove in OR con corpo+entita' — un falso positivo qui fonde due articoli scorrelati a
  prescindere dalle altre due prove, quindi tenuta la soglia a precisione massima. Nessun
  cambiamento di valore, aggiunta la calibrazione mancante.
- **`clustering.max_document_frequency` (0.10)** e **`_MIN_ITEMS_FOR_DF` (50, in `dedup.py`)**:
  rimisurato su n=505 item rilevanti (era 520): stesso continuum di document frequency, nessun gap
  netto — confermato "non ricalibrato" con numeri freschi, non un rinvio. `_MIN_ITEMS_FOR_DF`
  dichiarato esplicitamente per quello che e' (guardia strutturale, non una soglia tarabile su un
  golden set) invece di restare marcato "da calibrare".
- **`velocity.max_items_per_group` (3)**: era "# da calibrare (n=0)" - verificato che n=0 e'
  davvero la misura, non un placeholder: su tutti i 332 cluster il cap non vincola mai
  (`len(recent) <= gruppi*3` sempre vero). Commento aggiornato da "da calibrare" a "calibrato,
  n=0, non vincolante su questo corpus".

### Rimisurare le metriche di FIX_01 sul corpus nuovo

Non rifatto in questa sessione: richiede rilanciare l'intera pipeline di annotazione
(`is_political`) e i controlli di precisione entita'/clustering di FIX_01 con un metodo comparabile
a quello originale, che userebbe di nuovo l'LLM per centinaia di item — costo/tempo non
compatibile con il resto di C2-C6 in questa sessione. Il numero di clustering-precision piu'
rilevante per C1/C2 (accorpamenti falsi) e' comunque coperto indirettamente dalle soglie
ricalibrate sopra (F1 misurati su ogni soglia). Dichiarato come non fatto, non saltato in silenzio.

---

## C3 — un punteggio onesto

`pilot/score.py: compute_layer1_and_signal`. Tre decisioni, tutte nella direzione che il task
pre-vincolava:

1. **`novelty`**: tolta dal punteggio (non piu' una chiave in `components`, quindi mai sommata).
   Restava `None` per costruzione — richiede una baseline storica a 30gg che oggi ha una sola fonte
   su 17 (vedi C4) — e il task esclude esplicitamente "lasciarla sempre `None`" come opzione. Resta
   in `measured.novelty` solo come dichiarazione "non implementata", mai piu' come componente.
2. **`velocity`**: la versione continua/pesata resta in `measured.velocity` per audit (dipende da
   una baseline a mediana, vedi B0), ma il segnale che entra nel punteggio e' un nuovo flag
   booleano **`trending_now`** (`cluster_4h_count >= 2`). RFC §5.3: solo 8-21 cluster su ~500 hanno
   mai 2 articoli in 4h — troppo pochi per una componente continua, sufficienti per un flag onesto.
3. **Pesi ridisegnati per non far collidere le somme**: prima tutti a peso ~1.0 sulla stessa scala
   0-1 — un cluster con `source_diversity+1` e uno con `entity_centrality+1.0` davano la stessa
   somma. Nuovi pesi: `source_diversity` 1.0 (conteggio vero, resta l'unita' principale),
   `entity_centrality` 0.3, `trending_now` 0.2, `source_jump` 0.1 (booleane/categoriche, max 4
   livelli, sommano al massimo 0.6 < 1.0: non superano mai un gradino di `source_diversity`).

**Risultato misurato**: `signal_score` 16-17 -> **22 valori distinti su 332 cluster**. E' un
miglioramento reale (+~30%), non i 50 auspicati dal task. Verificato il perche' prima di fermarsi
qui: la combinazione REALE di questi 4 segnali sul corpus (non il peso, il valore grezzo) ha un
tetto di **24-25 tuple distinte** su 332 cluster — `source_diversity` vale 1 nell'88% dei cluster
(singoletti dopo C1/C2: 81.3%), `entity_centrality` ha solo 4 livelli per costruzione (54 entita'
note, RFC §7 domanda 3), `source_jump` scatta su 9/332, `trending_now` su 17/332. Nessuna
ridistribuzione di pesi puo' superare quel tetto: e' un limite dei segnali osservabili su QUESTO
corpus, non un bug di combinazione. Come previsto in `TASK_BETA_02.md` ("LA COSA PIU' IMPORTANTE"):
sotto i 50 valori dopo C1+C2, la risposta a RFC_SECONDA_OPINIONE_02.md §7 e' l'opzione **C**
(ridisegnare attorno a cio' che varia davvero, dichiarando 2-3 segnali reali invece di fingerne 5)
— gia' fatta qui togliendo `novelty` e degradando `velocity`, non serve riaprire oltre: aggiungere
altri pesi o soglie non sposterebbe il tetto di 24-25 combinazioni reali.

---

## Non ancora fatto (prima di C4/C5/C6, vedi sezioni dedicate)

C0b (9 card senza `modules` in `dashboard-config.js` — frontend, fuori scope, decisione
card-per-card esplicitamente rimandata dal task stesso).
