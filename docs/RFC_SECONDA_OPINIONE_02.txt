# RFC 02 — seconda opinione: il ranking ha cinque segnali dichiarati e uno e mezzo reali

Documento autosufficiente. Da dare a un'altra AI (Codex, Cursor, Gemini, DeepSeek, o un altro
Claude) **senza darle accesso al repo**. Tutto ciò che serve per rispondere è qui dentro.

**Non ti chiedo codice.** Ti chiedo come procederesti, e soprattutto **dove pensi che la mia
diagnosi sia sbagliata**. Ogni numero qui sotto è misurato sui file, non stimato.

Sostituisce `RFC_SECONDA_OPINIONE.md` (quello ha i numeri dell'era 293 item: non mescolarli).

---

## 1. Contesto

Radar politico-mediatico per la campagna elettorale in Republika Srpska / Bosnia-Erzegovina
(elezioni 4 ottobre 2026). Una dashboard mostra semafori per ~54 "protagonisti" (partiti,
candidati, istituzioni). Va alimentata con notizie vere invece che con scenari scritti a mano.

Pipeline, ~2.100 righe Python:

```
sources.yaml -> collect (RSS + sitemap + Wayback CDX) -> clean (boilerplate, url canonico, data, hash)
  -> dedup (stesso articolo) -> cluster (stesso evento) -> entity matching (54 protagonisti,
     alias latini + cirillici) -> signal_score -> SQLite FTS5 -> CLI
```

`signal_score` è una somma pesata di sole metriche osservabili, nessun giudizio:
`source_diversity + velocity + source_jump + novelty + entity_centrality`.

## 2. Vincoli non negoziabili

- **No overengineering.** Gestibile da una persona sola durante una campagna. Niente Kafka,
  Elasticsearch, vector DB, orchestratori.
- **Dipendenze ferme**: `feedparser` + `trafilatura`, tutto il resto stdlib (incluso un mini parser
  YAML fatto in casa). Nuove librerie: no.
- **Deve funzionare senza LLM.** L'AI è opzionale e va marcata.
- **Zero invenzione.** Dato non verificato = `null`.
- **Serbo, cirillico e latino insieme**, spesso nella stessa fonte. La normalizzazione e la
  traslitterazione esistono già e funzionano (coperte da test): non è un problema aperto.
- **La decisione politica resta umana.** Il sistema riduce il rumore e mostra le fonti.

## 3. Lo stato: il ranking è piatto

Corpus attuale: **1.284 item deduplicati, 17 fonti, 31 giorni civili coperti, 532 item "rilevanti"
(politici), 501 cluster.**

I cinque componenti di `signal_score`, su 501 cluster:

| segnale | valori distinti | cluster con valore != 0 |
|---|---:|---:|
| `source_diversity` | 6 (1...6) | 501 — ma **465 valgono 1** |
| `entity_centrality` | **4** | 439 |
| `velocity` | **2** (0.0 / 1.0) | 25 |
| `source_jump` | 2 | **2** |
| `novelty` | 1 | **0** — hardcoded `None` nel codice |

**`signal_score`: 16 valori distinti su 501 cluster** (min 1.0, max 7.0). Cioè: un ordinamento di
501 notizie su 16 gradini, con pareggi enormi, prodotto in pratica da
`source_diversity + entity_centrality` — e `source_diversity` vale 1 nel 93% dei casi.

**Il 95,8% dei cluster è un singoletto** (un articolo solo). È il numero che governa tutto:
`velocity` e `source_diversity` non possono accendersi su cluster da un articolo.

## 4. Cosa ho già escluso — non ripercorrerle

Quattro spiegazioni plausibili, tutte misurate, tutte false. Se la tua risposta le riporta, è a vuoto.

**a) "La colpa è di date sporche nel corpus."** 40 item su 1.627 raw hanno `published_at` fuori
finestra (fino al 1996: pagine sitemap non-articolo il cui `lastmod` viene letto come data di
pubblicazione). **Il filtro è stato scritto, applicato e la pipeline rilanciata.** Risultato:

| | prima | dopo il filtro |
|---|---:|---:|
| `window_actual_days` | 56 | **30** |
| bucket 4h non vuoti | 55,0% | **55,0%** |
| giorno dominante | 45,1% | **45,1%** |
| `velocity_baseline_4h` | 1 | **1** |
| `velocity`, valori distinti | 2 | **2** |
| singoletti | 95,8% | **95,7%** |
| `signal_score`, valori distinti | 16 | **16** |

Corregge un metadato e **non muove niente altro**. Non è questa la causa. Se la tua risposta
propone di filtrare le date, sappi che è già fatto e già misurato.

**b) "La colpa è del filtro di document frequency."** Il clustering esclude dal segnale-entità le
entità presenti in più del 10% degli item (il protagonista principale è nel 28%, il secondo nel 16%).
Riclusterizzando senza quel filtro: **94,7%** di singoletti invece di 95,8% — un punto — **e
ricompare un cluster da 63 item** che fonde tre eventi distinti. Il filtro costa poco e va tenuto.

**c) "La colpa è del filtro di rilevanza che scarta il 59% degli item."** Riclusterizzando **tutti**
i 1.284 item ignorando `is_relevant`: **94,8%** di singoletti. Un punto. Non è quello.

**d) "Le fonti non coprono gli stessi eventi."** Era la mia ipotesi preferita, ed è falsa. Sui 218
item rilevanti dei due giorni più densi ci sono **1.430 coppie cross-fonte** con titolo simile o
entità condivise, incluse diverse coppie a **titolo identico** su testate diverse. Le testate
ripubblicano continuamente lo stesso evento: il corpus non è rado di co-copertura.

## 5. Le tre cose che i dati indicano davvero

### 5.1 La soglia sul corpo non scatta MAI su una coppia vera

Il clustering accetta due articoli se **una** di tre prove passa: ≥2 entità-persona condivise,
**Jaccard su 4-grammi di caratteri del corpo ≥ 0.50**, oppure overlap di token del titolo ≥ 0.35.

Ho preso le coppie **cross-fonte con titolo quasi identico** (SequenceMatcher ≥ 0.85) — coppie di
cui sappiamo che sono lo stesso evento — e ho misurato il Jaccard del loro corpo:

```
16 coppie confermate stesso-evento, fonti diverse
  min 0.184 | p25 0.212 | mediana 0.245 | p75 0.346 | max 0.374
  sopra la soglia 0.50:  0 su 16  =  0%
```

**La prova del corpo non si attiva su nessuna coppia vera.** La soglia 0.50 era stata calibrata su un
golden set con **n=5 duplicati e n=3 stesso-evento**: è il numero più debole di tutta la pipeline, e
questo lo dimostra. La stessa soglia 0.50 è usata anche nel dedup.

Perché il corpo diverge tanto su articoli identici: le testate riscrivono e tagliano il lancio
d'agenzia, e una fonte ad alto volume consegna **solo il sommario RSS** — mediana **285 caratteri**,
79% degli item sotto 600 — contro una mediana di corpus di **1.760**. Lo shingling inoltre guarda
solo i primi 1.500 caratteri. Un blurb da 250 caratteri contro un articolo da 2.000 non può
somigliargli.

Sweep offline delle soglie sugli stessi 532 item (nessun file modificato):

| body | title | cluster | singoletti | cluster >1 | max |
|---:|---:|---:|---:|---:|---:|
| **0.50** | **0.35** (attuale) | 501 | **95,8%** | 21 | 7 |
| 0.35 | 0.35 | 480 | 92,5% | 36 | 7 |
| 0.25 | 0.35 | 438 | 89,0% | 48 | 9 |
| 0.20 | 0.35 | 394 | **83,8%** | 64 | 10 |
| 0.50 | 0.25 | 477 | 92,9% | 34 | 8 |
| 0.25 | 0.25 | 423 | 87,2% | 54 | 10 |

**Circa 12 punti di singoletti sono recuperabili ricalibrando.** Il costo in precisione **non è
misurato**: il golden set non ha abbastanza coppie per vederlo. È il rischio vero della mossa.

### 5.2 "30 giorni di storia" non è mai successo, tranne che per una fonte

L'obiettivo dichiarato era 30 giorni sulle 17 fonti già validate. Giorni distinti effettivamente
coperti, per fonte:

```
BL_IJ3_002   28 giorni,  83 item     <- l'unica che ha davvero 30gg
POL_RS_001   10 giorni, 111 item
BL_IJ3_001    9 giorni, 148 item
RS_ENT_002    6 giorni, 187 item
RS_ENT_001    2 giorni, 135 item
BL_IJ3_003    1 giorno,  91 item
FBIH_001      1 giorno,  98 item
SRC_009       1 giorno,  95 item
... le altre fra 1 e 7 giorni
```

Volume per giorno (31 giorni): 6, 39, 30, 15, 2, 4, 10, 3, 5, 14, 8, 6, 4, 39, 33, 46, 11, 12, 3, 1,
36, 8, 24, 12, 20, 7, 12, 21, 82, **180**, **565**.
**Mediana di fonti attive per giorno: 3 su 17.**

Il backfill via sitemap/Wayback ha funzionato dove esisteva un sitemap; le fonti solo-RSS danno la
finestra del feed, cioè 1-2 giorni. Il corpus non è "30 giorni x 17 fonti": è **una fonte per 28
giorni, più tutte le altre ammassate sugli ultimi due**.

Riclusterizzando le due fette separatamente:

| fetta | item | fonti | singoletti |
|---|---:|---:|---:|
| ultimi 2 giorni (7-12 fonti attive/giorno) | 218 | 12 | **92,7%** |
| giorni 3-30 (storia sottile, ~3 fonti/giorno) | 304 | 11 | **98,3%** |

La larghezza per giorno conta (6 punti), ma **anche la fetta più densa resta al 92,7%**.

### 5.3 Il tetto strutturale di `velocity`

`velocity` = articoli del cluster nelle ultime 4h / mediana di item per bucket da 4h. Contando la
**migliore** finestra da 4h di ogni cluster, non solo l'ultima del corpus:

```
cluster con max 1 articolo in 4h:  493
                      2 articoli:    5
                      3 articoli:    2
                      4 articoli:    1
```

**8 cluster su 501 hanno mai due articoli entro 4 ore.** E solo 21 su 501 hanno ≥2 item in assoluto.
Con qualunque denominatore e qualunque ancoraggio temporale, `velocity` non può diventare un segnale
distribuito su questo corpus. Anche portando i singoletti all'84% con la ricalibrazione di §5.1
resterebbe accesa su poche decine di cluster.

## 6. Il difetto di codice trovato (piccolo ma reale)

Il dedup ha 4 passaggi in cascata (url canonico -> content hash -> corpo ≥0.50 -> titolo ≥0.90 entro
48h). Ogni passaggio marca gli item come `used` e **i gruppi già formati sono chiusi**: il passaggio
4 salta ogni item già assorbito, quindi un gruppo creato al passaggio 2 o 3 non può più acquisire il
membro a titolo identico che il passaggio 4 troverebbe. Misurato: **12 coppie a `title_norm` identico
sopravvivono come item distinti**, tutte entro 48h, tutte cross-fonte. Piccolo in volume, ma è un
difetto di struttura, non una soglia.

## 7. LA DOMANDA

Non è "prima nuove fonti o prima ricalibrazione". È questa:

> **Un `signal_score` a 5 segnali è recuperabile su un corpus di media locali di questa forma, o va
> ridisegnato attorno a ciò che varia davvero?**

Sul corpus reale: `novelty` non è implementato, `source_jump` scatta 2 volte su 501, `velocity` è
tetto-limitata a poche decine di cluster anche nel migliore dei casi, `source_diversity` vale 1 nel
93% dei casi, `entity_centrality` ha 4 valori. Il risultato è un ordinamento a 16 gradini su 501
notizie.

Le opzioni che vedo, e su cui voglio il tuo parere:

- **A — Ricalibrare le soglie e basta** (§5.1). Costo basso, tutto offline, nessuna dipendenza.
  Guadagno misurato: singoletti 95,8% -> ~84%. Rischio non misurato: falsi accorpamenti, e il golden
  set non basta a vederli. Non accende né `velocity` né `novelty`.
- **B — Completare davvero il backfill** portando le fonti solo-RSS a 30 giorni via sitemap/Wayback
  (§5.2). Costo medio, riusa codice che esiste già. Guadagno atteso: fonti attive per giorno da ~3 a
  ~10; per estrapolazione dalla fetta densa, forse 3-6 punti di singoletti. Non è chiaro se basti a
  cambiare qualcosa nel ranking.
- **C — Cambiare il design del punteggio**: togliere `novelty` (non implementato) e `source_jump`
  (2 casi su 501), tenere `velocity` solo come flag binario onesto di "sta uscendo adesso", e
  costruire il ranking su ciò che ha davvero granularità — centralità delle entità, autorevolezza
  della fonte, freschezza continua — dichiarando che è un ranking a 2-3 segnali invece di fingerne 5.
- **D — Qualcosa che non ho considerato.** È l'opzione per cui scrivo questo documento.

Domande secondarie, se hai spazio:

1. Abbassare la soglia sul corpo a 0.25 senza un golden set adeguato è temerario? Esiste un modo
   **deterministico e senza LLM** di validare gli accorpamenti su qualche centinaio di coppie, dentro
   i vincoli di §2?
2. Con una fonte che consegna 285 caratteri mediani, ha senso tenerla nel clustering, o va marcata
   come "solo titolo" e trattata a parte?
3. `entity_centrality` con 4 valori distinti è oggi l'unico segnale che regge il ranking. È un
   problema di design della metrica, o è tutto ciò che si può ricavare da 54 entità note?
4. C'è un segnale osservabile, deterministico e a basso costo che sto ignorando, e che su un corpus
   di media locali dà più granularità di questi cinque?

---

## 8. RISPOSTA TROVATA — 2026-08-28: la metrica è quella sbagliata, non la soglia

Cercando come lo risolvono i progetti simili (Europe Media Monitor, NewsCatcher, letteratura sul
news story clustering) emerge **una sola pratica standard**: gli articoli si rappresentano come
**vettori TF-IDF di titolo + corpo**, e si confrontano con **coseno**, dentro una finestra temporale.
Nessuno usa Jaccard su n-grammi di caratteri del corpo grezzo.

Il motivo è matematico, e spiega esattamente i numeri di §5.1: **il Jaccard non è normalizzato per
lunghezza.** Un sommario RSS da 250 caratteri contro l'articolo da 2.000 che racconta lo stesso
evento non può superare `|A∩B|/|A∪B| ≈ 250/2000 = 0.12`, anche se ogni singolo 4-gramma del
sommario è contenuto nell'articolo. Il coseno TF-IDF normalizza per la norma del vettore: la
lunghezza sparisce.

Verificato sul corpus, con un TF-IDF coseno scritto in **15 righe di stdlib** (nessuna dipendenza
nuova, nessun LLM), sulle stesse 16 coppie confermate + 2.000 coppie a caso:

| | positivi (stesso evento, n=16) | negativi (a caso, n=2.000) | separa? |
|---|---|---|---|
| **Jaccard char-4gram** (attuale) | 0.184 – **0.374** | mediana 0.074, p95 0.117, **max 0.334** | **NO — si sovrappongono** |
| **TF-IDF coseno** (titolo+corpo) | **0.472** – 0.699 | mediana 0.012, p95 0.056 | **SÌ — margine 8×** |

E la prova che il Jaccard misura la lunghezza, non l'argomento:

```
len 242/1357  (rapporto 0.18)   jaccard 0.245   coseno 0.691
len 218/1968  (rapporto 0.11)   jaccard 0.197   coseno 0.472
len 295/ 988  (rapporto 0.30)   jaccard 0.374   coseno 0.695
```

Il Jaccard segue il rapporto di lunghezza quasi linearmente. Il coseno no.

**Conseguenza: abbassare `body_overlap_threshold` da 0.50 a 0.20 (opzione A di §7) è la cosa
sbagliata.** Il massimo dei negativi è 0.334: sotto 0.334 si iniziano a fondere coppie scorrelate,
e sopra 0.184 si perdono coppie vere. Non esiste una soglia buona per quella metrica su questo
corpus — ecco perché tutte le soglie provate danno o singoletti o cluster da 63 item.

Con il coseno TF-IDF una soglia fra **0.35 e 0.45** separa pulito (min positivi 0.472, p95 negativi
0.056), e diventa calibrabile sul serio perché i positivi si estraggono gratis dalle coppie
cross-fonte a titolo quasi identico.

**Questo risponde anche alla domanda 1 di §7** (come validare senza LLM e senza golden set): i
positivi sono le coppie a titolo quasi identico su fonti diverse, i negativi sono coppie a caso.
Entrambi deterministici, entrambi già nel corpus.
