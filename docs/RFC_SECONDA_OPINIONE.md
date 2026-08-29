# RFC — seconda opinione su una pipeline di ingestione che gira ma non funziona

Documento autosufficiente. Da dare a un'altra AI (Codex, Cursor, Gemini, DeepSeek, o un altro Claude)
**senza darle accesso al repo**. Tutto ciò che serve per rispondere è qui dentro.

**Non ti chiedo codice.** Ti chiedo come procederesti, e dove pensi che la mia diagnosi sia sbagliata.

---

## 1. Contesto in dieci righe

Radar politico-mediatico per una campagna elettorale in Republika Srpska / Bosnia-Erzegovina
(elezioni 4 ottobre 2026). Esiste già una dashboard funzionante che mostra semafori per ~54
"protagonisti" (partiti, candidati, istituzioni, territori).

Finora la dashboard girava su 160 scenari **scritti a mano**. Serve alimentarla con notizie vere.

È stato costruito un pilot di ingestione: fonti → raccolta → pulizia → dedup → clustering →
assegnazione valore → RAG. Il pilot **gira**, i test passano (14/14), il codice è pulito
(~2.100 righe Python, 2 sole dipendenze: `feedparser` e `trafilatura`, tutto il resto stdlib).

E i risultati sono inutilizzabili. Sotto ci sono i numeri veri.

## 2. Vincoli non negoziabili

Vengono dal progetto, non sono preferenze estetiche:

- **No overengineering.** Il sistema deve restare gestibile da una persona sola durante una campagna.
  Niente Kafka, Kubernetes, microservizi, Elasticsearch, vector DB, framework di orchestrazione.
- **Deve funzionare senza LLM.** L'AI è opzionale e va marcata. Le funzioni base sono deterministiche.
- **Zero invenzione.** Se un dato non è verificato è `null`. Niente punteggi inventati, niente
  geografia elettorale dedotta, niente fonti presunte.
- **Ogni segnale risale alla fonte originale.** Un item senza URL non esiste.
- **Serbo, cirillico e latino insieme.** Nella stessa fonte, spesso nello stesso giorno.
  `Ненад Стевандић` e `Nenad Stevandić` sono la stessa persona.
- **La decisione politica resta umana.** Il sistema riduce il rumore e mostra le fonti. Non decide.

## 3. Cosa fa la pipeline, in breve

```
sources.yaml → collect (RSS/HTML) → clean (boilerplate, canonical url, date, hash)
   → dedup (stesso articolo) → cluster (stesso evento)
   → entity matching (54 protagonisti, alias latini + cirillici)
   → signal_score (solo metriche misurate) → SQLite FTS5 → CLI di interrogazione
```

`signal_score` è una somma pesata di sole metriche osservabili:
`source_diversity`, `velocity`, `source_jump`, `novelty`, `entity_centrality`.
Nessun campo di giudizio (rischio, priorità, gravità) viene scritto come fatto: vive in un blocco
separato marcato `MODEL` o `ANALYST`, oggi vuoto.

## 4. I numeri veri della prima run

```
Fonti candidate provate         14   (fetch HTTP reale)
Fonti dichiarate pronte         10
Fonti che consegnano davvero     7   (3 verificate ma senza parser di listing → 0 item)

Articoli scaricati             293
Dopo pulizia                   245   (48 scartati: testo troppo corto)
Dopo dedup                     244   ← 1 solo duplicato trovato
Cluster                        240   ← 236 da 1 articolo, 4 da 2

Item con almeno un protagonista 117 / 244
```

Copertura temporale reale, per fonte (la finestra richiesta era 7 giorni):

```
RTRS         100 articoli  →  1 solo giorno
Srpskainfo    50 articoli  →  1 solo giorno
SNSD          10 articoli  →  1 solo giorno
Banjaluka24   20 articoli  →  2 giorni
Glas Regije   10 articoli  →  2 giorni
ATV          100 articoli  →  5 giorni
Pod lupom      3 articoli  →  3 giorni
```

Due fonti (RTRS + ATV) sono 200 articoli su 293, cioè il 68% del corpus. Entrambe sono emittenti
di Banja Luka. Il campo che dovrebbe segnalare la proprietà editoriale comune è `null` per tutte.

I cinque cluster con il punteggio più alto:

```
2.93   Minić apre il Festival dei prodotti locali
2.63   Nessun referto medico dall'Aja sul generale
2.60   Il leader dei pensionati rivela l'importo della sua pensione
2.33   Tragedia: una vespa uccide un uomo
2.33   Scena vergognosa: sangue nel fiume?
```

Il protagonista più frequente del corpus è "Predsjedništvo BiH" con 49 hit su 244. Fra questi:

```
"Трагедија у БиХ: Пчела усмртила мушкарца"   →  taggato Presidenza della BiH
"Срамотан призор у БиХ: Ријеком тече крв?"   →  taggato Presidenza della BiH
```

385 errori HTTP 400 su 388 totali, tutti dalla stessa fonte, tutti su URL della forma
`http://host:443/path` — scheme `http` su porta 443, pubblicati così dal feed originale.

## 5. La mia diagnosi

Quattro meccanismi spenti, in ordine di impatto. **Contestala dove non ti convince.**

**A. La finestra di 7 giorni non è mai esistita.** I feed RSS sono tappati a N entry. Per una TV che
pubblica ~50 pezzi al giorno, 100 entry sono due giorni. Ogni metrica temporale — `velocity` contro
baseline, `novelty` sui 30 giorni, `source_jump`, la finestra di clustering — gira su un corpus che
per le fonti principali è di **un giorno**. Non è un problema di soglie: i dati non ci sono.

**B. Gli alias multi-parola matchano su un token solo.** `Predsjedništvo BiH` viene cercato parola per
parola, quindi basta `BiH`, che compare in un titolo su due. Da qui i 49 hit e la vespa presidenziale.
Stessa dinamica per keyword generiche usate come alias: `mandat`, `finansiranje`.

**C. Il dedup guarda solo il titolo.** La catena è: hash del contenuto → titolo identico →
similarità sul titolo ≥ 0.90 entro 48h. Nessun confronto sul corpo. Un portale che riprende un
comunicato riscrive il titolo, quindi il duplicato non viene visto. Da qui 1 duplicato su 245.

**D. Il clustering è di fatto un no-op.** Confronta solo la sovrapposizione di token fra titoli
(Jaccard ≥ 0.35), non usa le entità nonostante il codice dichiari di farlo, e confronta ogni candidato
solo contro il primo elemento del gruppo, mai contro gli altri membri. Da qui 236 cluster da un articolo.

Quando scatta, però, funziona: ha unito `Минић у Бањалуци отворио девети Фестивал домаћих производа`
con `Minić otvorio Festival domaćih proizvoda u Banjaluci`. Cirillico e latino si agganciano.

**Nota sul punteggio.** I cluster in cima non sono un difetto dei pesi: sono la conseguenza di A+B+C+D.
La mia posizione è che **ricalibrare i pesi adesso significherebbe calibrare sul rumore**.

---

## 6. COSA TI CHIEDO

Rispondi in prosa, non in codice. Massimo due pagine. In quest'ordine:

### 6.1 — Dove sbaglio
La parte più utile della tua risposta. Quale punto della diagnosi (A, B, C, D) non regge?
C'è una causa comune che non ho visto? Sto trattando come rotto qualcosa che è solo mal calibrato,
o viceversa?

### 6.2 — Il tuo ordine di intervento
Quali due interventi faresti **per primi** e perché. Se il tuo ordine è diverso dal mio (A, B, C, D),
dillo e spiega cosa ti aspetti che cambi a valle.

### 6.3 — Il problema della finestra temporale
Un feed RSS non contiene 7 giorni di una testata ad alto volume. Come ci arrivi, dato che il sistema
deve restare semplice e girare durante una campagna?
Considera: accumulo nel tempo, backfill da sitemap o archivio paginato, API esterne, altro.
Dimmi anche cosa **non** faresti e perché.

### 6.4 — Dedup e clustering fra cirillico e latino
Come identificheresti che due articoli parlano dello stesso evento, quando uno è in cirillico e l'altro
in latino, i titoli sono riscritti, e il vincolo è: niente vector database, niente servizi esterni,
Python stdlib più due librerie.
Se secondo te il vincolo va rotto, **argomenta il costo** — chi manutiene la cosa in più durante
una campagna elettorale.

### 6.5 — Entità politiche in un corpus generalista
Metà del corpus è cronaca, sport, salute. Come eviteresti che acronimi ambigui (`US`, `BiH`, `RS`, `SP`)
e parole comuni (`mandat`, `finansiranje`) generino falsi positivi, senza perdere le menzioni vere?
Sto valutando la co-occorrenza obbligatoria di una seconda entità: dimmi se è sufficiente o dove si rompe.

### 6.6 — Come misureresti che è migliorato
Ho un golden set annotato a mano di 30 item e sto per portarlo a 100. Sono pochi? Quali metriche
guarderesti per prime, e qual è secondo te la soglia sotto cui il sistema **non va messo in mano
a un utente**, perché il rumore costa più del segnale?

### 6.7 — Il rischio che non ho nominato
Uno solo, quello che consideri più serio. Non un elenco.

---

## 7. Regole per la risposta

- Se un numero di questo documento contraddice la tua intuizione, **fidati del numero**: viene da
  un'ispezione diretta dei file, non da un report generato.
- Non proporre di riscrivere tutto da capo senza dire cosa si perde. Il codice esistente è pulito
  e testato: il problema è nei meccanismi, non nella qualità.
- Non proporre uno stack più grande senza dire chi lo manutiene.
- Se pensi che il vero problema sia a monte — le fonti, la scelta del corpus, la definizione stessa
  di "evento" — dillo. È la risposta che vale di più.
