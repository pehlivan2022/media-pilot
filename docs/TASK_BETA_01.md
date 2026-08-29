# TASK BETA 01 — allargare finestra e fonti, e far vivere i segnali

**Rev. 1** — scritto dopo il report di `TASK_FIX_01.md`, verificando i file veri (`data/clean.jsonl`,
`data/scored_clusters.jsonl`, `config/`), non il report.

FIX_01 ha fatto quello che prometteva: filtro, entità, dedup e clustering ora funzionano e sono
misurati. Questo task non li rimette in discussione.

Il problema che resta è diverso: **il livello di ranking è spento.** Quattro dei cinque segnali di
`signal_score` non variano. Non perché siano rotti, ma perché un corpus largo un giorno non può
esprimerli — più un bug di unità introdotto proprio da FIX 3.

Allargare finestra e fonti non è un miglioramento cosmetico per la beta: **è la precondizione perché
il punteggio significhi qualcosa.**

## REGOLE

- Stessi vincoli: **no overengineering**, dipendenze ferme a `feedparser` + `trafilatura`, resto
  stdlib. Wayback, GDELT e Google News sono chiamate HTTP: nessuna libreria nuova.
- **Il testo originale non si traslittera mai** (regola di FIX_01, invariata).
- Ogni fase chiude con il suo **numero prima/dopo**. Una fase senza numero è un'intenzione.
- **Non riscrivere `config/sources.yaml` da zero.** `sources.py` lo rigenera e cancellerebbe le
  modifiche manuali di FIX 3/4 — errore già evitato una volta, non rifarlo. Aggiunte additive.
- Dove una fonte esterna non è verificabile, **si dichiara e si misura**, non si assume.

---

## LE PROVE

Numeri estratti dai file al 2026-08-28, non dal report.

```
corpus live: 784 item puliti, 17 fonti, 150 cluster

articoli per giorno:
  08-20    1
  08-21    6
  08-22    4
  08-23    7
  08-24   19
  08-25   79
  08-26  189
  08-27  479     <- 61% del corpus in un solo giorno

bucket da 4h NON VUOTI: 28 su 48 attesi (span reale 7 giorni)
baseline_4h come calcolata (mediana dei soli bucket non vuoti):  6
baseline_4h se si contassero anche i bucket vuoti:               2

I CINQUE SEGNALI, su 150 cluster:
  velocity            solo 2 valori:  0.0 (128 cluster) | 0.167 (22 cluster)
  novelty             None su 150/150                            -> morto
  source_jump         True su 3/150 (2%)
  source_diversity    = 1 su 126/150 (84% singoletti)
  entity_centrality   l'unico che varia davvero

  signal_score: 19 valori distinti su 150 cluster, min 1.0 max 6.0

concentrazione fonti: RTRS 25.6% + ATV 21.9% = 47.5% | top 4 fonti = 73%
```

**Conclusione: `signal_score` è di fatto un ranking a un segnale (`entity_centrality`) travestito da
cinque.** Il "radar" oggi ordina le notizie per quante entità note contengono, e per poco altro.

---

## STATO — B0 e B4a sono FATTI (2026-08-28)

Fatti in una sessione parallela, con i numeri qui sotto. **Non rifarli.** Restano B1, B2, B3 e il
resto di B4.

| | prima | dopo |
|---|---|---|
| `velocity`, valori distinti | 2 (0.0 / 0.167) | **3** (0.0: 140, 0.5: 25, 1.0: 1) |
| `velocity_baseline_4h` | 6 (solo bucket non vuoti) | **2** (con i vuoti) |
| item con entità `dodik` | 0 | **52** |
| cluster con `dodik` | 0 | 32 → 24 dopo il guard df |
| test | 17/17 | **19/19** (`test_13`, `test_13b`) |

File toccati: `pilot/score.py`, `pilot/dedup.py`, `pilot/test_pipeline.py`, `config/scoring.yaml`,
`dashboard-config.js`, `config/entities.yaml` (rigenerato).

**`velocity` non è ancora un segnale vivo, e non lo sarà finché non arriva B1/B2.** Il bug di unità
è corretto e `test_13` lo dimostra (10 articoli da 2 fonti battono 1 articolo da 1 fonte). Ma sul
corpus attuale il terzo valore viene da **un solo cluster**: con l'82% di singoletti non c'è quasi
mai più di un articolo per cluster nella stessa finestra di 4h. Il fix è giusto, il corpus non lo
sa ancora esercitare — è esattamente il lavoro di B1 e B2.

**Trappola da conoscere prima di toccare le entità**: `score.py:98` riusa gli `_entity_hits` già
salvati in `items.jsonl` e li ricalcola solo se mancano. Dopo ogni modifica a `dashboard-config.js`
va rilanciato `python -m pilot.entities` **e poi `python -m pilot.dedup`**, non solo `pilot.score`:
altrimenti la nuova entità non compare e sembra che il match non funzioni.

**Regressione trovata e chiusa, da non riaprire.** Aggiungere `dodik` (28.1% degli item rilevanti)
accanto a `minic` (15.7%) ha fatto ricomparire il collasso che FIX 2 aveva chiuso: con
`min_shared_entities: 2` quelle due entità bastavano a fondere **18 articoli e tre eventi distinti**
(commemorazione Mladić + Kočićev zbor + sentenza Jahorina) in un cluster unico, che finiva **primo
nel radar con `signal_score` 13.1**. Il filtro per tipo di FIX 2 non bastava: `dodik` è `type: actor`,
ma la sua frequenza documentale lo rende non discriminante.

Chiuso con `clustering.max_document_frequency: 0.10` in `config/scoring.yaml`: le entità presenti in
più del 10% degli item rilevanti sono escluse dal **segnale di clustering** (restano nel punteggio e
nelle card). Il gap nel corpus è netto — dodik 28.1%, minić 15.7%, poi stanivuković 7.6% — e 0.10 ci
sta in mezzo. Sotto 50 item il filtro non si attiva (`_MIN_ITEMS_FOR_DF`): su un batch piccolo la
frequenza è rumore, non misura.

**Il prezzo, dichiarato**: la storia Mladić, che è un evento vero coperto da ~9 articoli, ora si
spezza in 3 cluster (5 + 3 + 1) invece di uno. È il compromesso che il task originale chiedeva
("meglio due cluster separati che due eventi diversi fusi"), ma **è recall perso e va rimisurato in
B3**, insieme a `max_document_frequency` che oggi è scelta su un solo corpus.

---

## B0 — Il bug di unità in `velocity`  ✅ FATTO

**Va fatto per primo, e non è un problema di dimensione del corpus.** È una regressione introdotta da
FIX 3, e allargare il corpus la peggiora invece di risolverla.

In `pilot/score.py`, `compute_layer1_and_signal`:

```
cluster_4h_count = len(recent_groups)   # conta GRUPPI DI FONTI distinti (range reale 1-4, tetto 17)
baseline_4h      = 6                    # conta ITEM per bucket da 4h
velocity         = cluster_4h_count / baseline_4h
```

Numeratore e denominatore hanno **unità diverse**. FIX 3 ha cambiato il numeratore da articoli a
gruppi ("velocity ora conta gruppi/fonti distinte, non articoli grezzi") e ha lasciato il denominatore
come conteggio di item. Effetti misurati:

- velocity assume solo 2 valori: `0.0` se nessun membro è nelle ultime 4h, `1/6 = 0.167` se ce n'è uno.
  Non è una velocità, è **un flag di recency da 4 ore diviso 6**.
- Con più fonti e più storia, `baseline_4h` cresce e velocity **diminuisce**: il segnale peggiora
  proprio mentre il corpus migliora.

Secondo difetto, **distinto e da non confondere col primo**: `bucket_counts` non crea mai i bucket
vuoti, quindi la mediana è calcolata solo sui bucket non vuoti (misurato: 6 invece di 2). Questo è un
artefatto di campionamento e si risolve da solo quando la finestra è piena — **il primo no.**

**Cosa fare**

1. Rendere numeratore e denominatore omogenei. Scelta consigliata (più semplice, non l'unica):
   numeratore = **articoli** del cluster nelle ultime 4h; il tetto anti-gonfiaggio di FIX 3 resta, ma
   applicato come cap (`min(articoli, n_gruppi_distinti * k)`), non sostituendo l'unità.
   Se scegli diversamente, **dichiara perché** e misura entrambe le varianti sul corpus.
2. Creare i bucket vuoti nell'intervallo `[min(published_at), max(published_at)]` prima della mediana.
3. `velocity` resta `None` se `window_actual_days < 3` (già presente, non toccare).

**Done quando**: `measured.velocity` assume **più di 2 valori distinti** sul corpus attuale, e un test
sintetico verifica che un cluster con 10 articoli in 4h da 2 fonti abbia velocity maggiore di un
cluster con 1 articolo in 4h da 1 fonte. Oggi hanno lo stesso identico valore.

---

## B1 — Allargare il periodo (prima delle fonti)

**L'ordine è vincolante e va contro la lettura più immediata della richiesta.** Motivo: le soglie di
FIX_01 (`body_similarity_threshold` 0.50 su n=5/3, `clustering.window_hours` 60 mai calibrata) e il
golden set da 100 item sono tarati **sul mix di fonti attuale**. Aggiungere fonti prima sposta la
distribuzione sotto soglie che nessuno rimisura. Allargare la storia sulle 17 fonti già validate non
cambia il mix, riaccende i segnali temporali, e **allarga il bacino da cui pescare un golden set più
grande** per la ricalibrazione di B3.

**Obiettivo: 30 giorni di storia sulle fonti esistenti.**

1. **Estendere il backfill sitemap** già scritto e funzionante in FIX 4 (Transparency BiH +6, BN +4):
   stesso protocollo standard `sitemapindex → foglie → lastmod`, nessun parser per testata, ma finestra
   a 30 giorni invece di 7 e applicato a **tutte** le fonti che espongono un sitemap, non solo alle due
   senza RSS.
2. **Wayback CDX API** per la storia che il sitemap non copre — gratis, senza chiave, una GET:

   ```
   http://web.archive.org/cdx/search/cdx?url=<dominio>/*&from=<YYYYMMDD>&to=<YYYYMMDD>&output=json&fl=original,timestamp&collapse=urlkey&filter=statuscode:200&limit=5000
   ```

   Restituisce la lista di URL archiviati; il testo si prende con `trafilatura` dall'URL vivo, e solo
   se quello fallisce da `http://web.archive.org/web/<timestamp>/<url>`.
   **Verificare prima su una fonte sola**, non su 17 in parallelo: è un servizio pubblico gratuito,
   rate-limit non documentato, va trattato con garbo (pausa tra le richieste, una fonte per volta).
3. Ricalcolare `window_actual_days` per fonte e riscriverlo in `config/sources.yaml` (additivo).

**Done quando**:

- bucket da 4h non vuoti ≥ **70%** dei bucket attesi sulla finestra coperta (oggi: 28/48 = 58%, con
  il 61% del volume in un giorno solo)
- nessun singolo giorno vale più del **25%** del corpus (oggi: 61%)
- `novelty` smette di essere `None` — richiede i 30 giorni di storia che il commento in `score.py`
  già nomina. Se dopo il backfill resta `None`, **dire perché**, non lasciarlo muto.

---

## B2 — Allargare le fonti

Solo dopo B1. Tre vie, in ordine di costo crescente.

**a) Recuperare le fonti perse con quello che c'è già.**

- `Capital.ba` — BLOCKED, HTTP 403 in diretta. Le pagine archiviate su Wayback (B1.2) non danno 403.
- `Dobojski.info` — MANUAL_ONLY, nessun sitemap stabile. Stessa via: CDX sul dominio.

Costo: zero codice nuovo, riusa B1.2. **Farlo per primo.**

**b) Google News RSS come strato di scoperta per protagonista.**

Usa `feedparser`, già installato. Una query per protagonista di `config/entities.yaml`:

```
https://news.google.com/rss/search?q=%22<nome>%22&hl=sr&gl=BA&ceid=BA:sr
```

Restituisce titolo + link all'editore originale, non il testo: il testo lo prende `trafilatura`, come
per tutto il resto. Serve a raggiungere testate fuori dalle 17, incluse quelle che bloccano il fetch
diretto. **Limiti da dichiarare, non da nascondere**: è un endpoint non documentato, senza garanzie di
stabilità, con rate-limit non pubblicato, e la copertura per `gl=BA` va misurata, non assunta.
Fermarsi se dà meno di ~5 item nuovi per protagonista su 30 giorni: non varrebbe il codice.

**c) GDELT DOC 2.0 — VERIFICARE PRIMA, ADOTTARE SOLO SE PASSA.**

Potenzialmente il guadagno di copertura più grande (gratis, senza chiave, aggiornato ogni 15 min,
metadati già estratti). **Non l'ho potuto verificare**: dall'ambiente in cui è stato scritto questo
task `api.gdeltproject.org` va in timeout (`http_code=000`, due tentativi) mentre `klix.ba` risponde
200 — è un blocco dell'ambiente, non un giudizio su GDELT.

### VERIFICATO IL 2026-08-28 — e la prova che avevo scritto era quella sbagliata

**GDELT è raggiungibile. Usare `http://`, non `https://`.** Il timeout riportato da entrambe le
sessioni era una diagnosi errata: DNS risolve (`104.197.47.124`), **la porta 80 apre, la 443 no**,
mentre `klix.ba:443` funziona dallo stesso ambiente. Non è un blocco di rete generico, è la sola
443 di quell'host. Su `http://` l'API risponde in pochi secondi.

**La prova di accettazione che avevo scritto (`domain:<dominio>`) misurava la cosa sbagliata**:
chiedeva se GDELT ricopre domini che sono *già* nelle 18 fonti — informazione inutile. Risultato di
quel test, per completezza: 2 domini su 8 non-zero (`rtrs.tv` 75 = tetto di maxrecords, già la fonte
#1 col 25.6% del corpus; `nezavisne.com` 8). Klix, ATV, Glas Srpske, Srpskainfo, Capital: zero.

**La prova giusta è per paese**, perché lo scopo di B2 è trovare testate che NON hai:

```
http://api.gdeltproject.org/api/v2/doc/doc?query=sourcecountry:BK%20(Dodik%20OR%20SNSD%20OR%20izbori)&mode=artlist&maxrecords=100&timespan=7d&format=json
```

Risultato reale: **34 articoli, 7 domini distinti, 6 dei quali NON sono fra le 18 fonti** —
`slobodna-bosna.ba` (14), `avaz.ba` (9), `faktor.ba` (3), `bosnjaci.net` (2), `vecernji.ba` (2),
`federalna.ba` (2). Il record dà `url`, `title`, `seendate`, `domain`, `language`: il testo lo
prende `trafilatura`, come per tutto il resto.

**Verdetto onesto: guadagno reale ma fuori bersaglio.** Quei domini sono quasi tutti della
Federazione / Sarajevo (avaz, faktor, klix, federalna, slobodna-bosna) o croati (vecernji): servono
a vedere **come la politica RS viene raccontata fuori dalla RS** — che per un radar politico vale,
ed è materia da `source_jump` — ma **non densificano la copertura locale della RS**, che è il
problema vero dell'83% di singoletti. Non aspettarsi che GDELT chiuda B1/B2: è uno strato in più,
non la soluzione.

Da fare: aggiungerlo come fonte di scoperta a bassa priorità **dopo** che B1 è finito e misurato,
e correggere la riga GDELT in `docs/SOURCE_AUDIT.csv` (oggi dice NON PASSA per timeout: il motivo
è sbagliato).

**Scartati, non riproporre**

- `news-please` — sostituirebbe `collect.py`/`clean.py` che funzionano, e usa newspaper/readability al
  posto di `trafilatura`: peggiora l'estrazione. Non adottare.
- Common Crawl CC-NEWS — scala TB, per una storia più profonda di 30 giorni. Rimandato, non escluso.
- NewsAPI.org — tier gratuito ritardato di 24h e solo sviluppo. Inutile qui.
- Event Registry / NewsAPI.ai — non abbastanza gratuito per il volume che serve.

**Done quando**:

- `source_diversity = 1` scende sotto il **70%** dei cluster (oggi 84%)
- nessuna coppia di fonti supera il **35%** del corpus (oggi RTRS+ATV = 47.5%)
- ogni fonte tentata e scartata è una riga in `docs/SOURCE_AUDIT.csv` con il motivo

---

## B3 — Ricalibrare, perché il mix è cambiato

B1 e B2 spostano la distribuzione. Le soglie di FIX_01 non valgono più automaticamente, e il golden
set da 100 item non è più rappresentativo.

1. Estendere il golden set pescando **dal corpus nuovo** (storia + fonti nuove), non da quello vecchio.
   Priorità alle coppie: le soglie di dedup/clustering sono tarate su n=5 duplicati e n=3 stesso-evento,
   ed è il numero più debole di tutto FIX_01.
2. Ricalibrare in quest'ordine: `dedup.body_similarity_threshold` → `clustering.body_overlap_threshold`
   → `clustering.window_hours` (mai calibrata finora) → `clustering.max_document_frequency` e
   `_MIN_ITEMS_FOR_DF` (introdotti in B4a su un solo corpus, vedi STATO: costano recall sulle storie
   grandi, e la soglia giusta cambia quando il corpus si allarga).
3. Rimisurare le metriche di FIX_01 sul corpus nuovo: `is_political` (era 83 / 88.9 / 63.2),
   precisione entità (94.4% su actor/party), precisione clustering (100% su 49 coppie DIVERSI).
   **Un calo qui è informazione, non un fallimento** — va riportato.

**Done quando**: ogni soglia in `config/scoring.yaml` ha accanto `n=` del campione su cui è stata
calibrata, e nessuna resta con `# da calibrare`.

---

## B4 — Dashboard beta

**SBLOCCATA.** L'utente ha aperto il frontend il 2026-08-28: `dashboard-config.js` e gli altri file
di frontend sono modificabili. Il divieto di FIX_01 ("non toccare il frontend") **non vale più**.

`Milorad Dodik` — con ogni probabilità il protagonista singolo più rilevante della Republika Srpska —
**non compare né in `dashboard-config.js` né in `config/entities.yaml`** (0 occorrenze, verificato).
Il report di FIX_01 lo aveva dichiarato fuori scope proprio per quel divieto. Ora è la prima cosa da
sistemare in questa fase: finché manca, il radar non vede l'attore principale.

Regola che resta valida: `radar.js` e `data.js` (che ha già lo switch `mode:'api'`) vanno **alimentati,
non riscritti** — vedi `docs/PROJECT_AUDIT.md`.

In questa fase rientrano:

- ~~Dodik nelle card~~ **FATTO** (card `dodik` in KONKURENTI, base:2, gli altri bumpati di 1)
- ~~alias solo-cognome per `minic`~~ **FATTO** (`Minić`/`Minic`; le forme cirilliche le genera
  `pilot/entities.py`, **non vanno scritte a mano** nelle `keywords`)
- alias solo-cognome per gli **altri** protagonisti: **non fatto di proposito.** `Trninić` è il
  cognome di due candidati diversi (Milan IJ6 e Aleksandar IJ2) e `Radović`/`Kovač`/`Ivanović` sono
  cognomi comunissimi: il solo cognome li renderebbe ambigui. Serve una decisione caso per caso,
  non una regola.
- **`Игор Додик` (il figlio) matcha l'alias `Додик`: misurato 4 item su 52 (7.7%)** — fra cui una
  donazione di laptop e un pezzo su una cantante. Lasciato così **di proposito**: dei 52 item, 34
  nominano Milorad per esteso e **14 usano solo il cognome** e sono veri. Togliere l'alias
  solo-cognome costerebbe 14 veri positivi per evitarne 4 falsi — trade sbagliato. Una card
  `igor-dodik` separata **non basta**: `match_entities` valuta ogni entità in modo indipendente
  (`entities.py:385`), non ha disambiguazione fra entità sovrapposte, quindi quei 4 item
  prenderebbero entrambi i moduli. Serve un meccanismo di contesto negativo che oggi non esiste:
  **da decidere in B3**, con il numero sopra, non da improvvisare qui.
- `script: latn` dichiarato per tutte e 17 le fonti in `config/sources.yaml`, mentre **506 item su 784
  (65%) contengono cirillico**. Il matching funziona lo stesso (`lat_to_cyr` / `normalize_search`
  esistono e `test_3` li copre), ma il metadato dichiarato è falso. Da correggere anche solo per
  onestà del dato. Nota: l'euristica in `sources.py:301` (`'cyrl' if row.get('napomena','') else
  'latn'`) marca cirillica qualunque fonte abbia una nota non vuota — è sbagliata a prescindere.

---

## ORDINE

```
B0  bug di unita' velocity   <- codice, non dipende da niente, sopravvive all'allargamento
B1  finestra a 30 giorni     <- sulle 17 fonti gia' validate, non cambia il mix
B2  fonti nuove              <- a) recupero perse  b) Google News  c) GDELT se passa la verifica
B3  ricalibrazione           <- obbligatoria dopo B1+B2, il mix e' cambiato
B4  dashboard                <- sbloccata 2026-08-28, frontend modificabile
```

**B4a (Dodik + alias solo-cognome) si puo' anticipare a subito dopo B0**: non dipende ne' dalla
finestra ne' dalle fonti nuove, e ogni run fatta senza di lui produce un ranking che sbaglia il
protagonista principale. Il resto di B4 (rendering, alimentazione di `data.js`) resta dopo B3.

## LA COSA PIÙ IMPORTANTE

Se dopo B1 e B2 `velocity` ha ancora 2 valori, `novelty` è ancora `None` e `source_diversity` è ancora
1 nell'84% dei cluster, **allora l'allargamento non è servito e il punteggio resta a un segnale solo.**
Sono quelle tre misure a dire se questo giro è riuscito — non il numero di fonti né di articoli.
