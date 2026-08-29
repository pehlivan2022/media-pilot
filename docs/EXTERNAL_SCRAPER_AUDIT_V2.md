# EXTERNAL SCRAPER AUDIT V2

Date: 2026-08-29. `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md` §3. Tutti e 6 i repository esistono
davvero — nessun `REPO_NOT_FOUND` — ma nessuno passa un audit onesto contro i vincoli reali di questo
progetto. Ogni riga sotto cita cosa e' stato fetchato dal vivo (`gh api`/`gh search`, non training data)
e cosa contiene realmente.

**Verdetto finale: REJECT su tutti e 6.** Nessun adapter costruito, nessun pilot lanciato (§3 della task
lo permette esplicitamente come esito legittimo: "non forzare una scelta debole solo per avere qualcosa
da costruire"). Dettaglio per candidato sotto; motivazione aggregata in fondo.

---

## 1. `alphap365/open-news`

**Esiste**: si — `gh api repos/alphap365/open-news` → Python, MIT, 1 star, creato 2026-05-16, ultimo push
2026-06-29 (attivo, non abbandonato). Pubblicato su PyPI come `open-news-api` v0.2.0.

**Cosa fa davvero** (letto `pyproject.toml` + `requirements.txt` + README dal vivo):
- Estrazione articolo (lxml-based, built-in, no newspaper3k/trafilatura).
- Feed RSS curati per 50+ paesi, registro esterno `alphap365/open-feeds` (repo separato, verificato dal
  vivo: cartelle `feeds/`, `templates/`, `index.json` — **nessuna Bosnia/Serbia/Balcani nel registro**,
  `grep -i "bosn|serb|balkan"` sui nomi contenuti in `open-feeds` = 0 risultati).
- Ricerca Google News con decodifica URL via il pacchetto separato `googlenewsdecoder`.
- Discovery RSS automatica (BeautifulSoup + regex sui link `<link rel=alternate>` + path comuni) — **la
  stessa tecnica gia' usata da `pilot/sources.py`** (vedi `find_feed_link()`/`FEED_PATHS` in quel file),
  non un metodo nuovo.

**Dipendenze reali** (`requirements.txt`): `lxml, python-dateutil, httpx, beautifulsoup4, feedparser,
googlenewsdecoder, requests`. `feedparser` gia' nostro; le altre 6 sarebbero NUOVE. Il progetto ha un
vincolo esplicito e mai revocato in `docs/TASK_SCRAPER_PILOT.md` (§VINCOLI HARD): **"Dipendenze totali
ammesse: 2 — feedparser, trafilatura. Tutto il resto e' stdlib."** Aggiungere `open-news-api` porta le
dipendenze totali del progetto da 2 a 8+ (contando le transitive di `googlenewsdecoder`, vedi sotto) —
viola da solo questo vincolo, indipendentemente dal resto della valutazione.

**Il pezzo di reale valore — Google News decode — verificato dal vivo, non solo dal README**:
`googlenewsdecoder` (fonte reale: `SSujitX/google-news-url-decoder`, 297 star, MIT, attivo) NON e' una
decodifica offline. Letto `new_decoderv3.py` dal vivo: estrae un base64 dall'URL, poi fa una CHIAMATA DI
RETE in piu' all'endpoint interno non documentato di Google (`batchexecute`) per ottenere
signature+timestamp e risolvere l'URL reale — esattamente il tipo di endpoint privato reverse-engineered
che l'audit precedente (`docs/SOURCE_AUDIT.csv`, riga `GOOGLE_NEWS_RSS`) aveva gia' scartato per lo stesso
motivo ("violerebbe no nuove dipendenze/no overengineering"). Il repository ha **4 versioni di decoder
diverse** (`decoderv1`-`v4`, poi `new_decoderv1`-`v3`) — segno concreto che Google cambia lo schema e la
libreria rincorre le rotture: costo di manutenzione reale, non ipotetico. Inoltre `new_decoderv3.py`
importa `selectolax`, una dipendenza transitiva NON dichiarata nel `requirements.txt` di `open-news`
stesso — l'albero delle dipendenze reale e' piu' grande di quello che il README lascia intuire.

**RS/BiH fit**: zero feed curati Balcani (verificato sopra). L'unico canale possibile per contenuto RS/BiH
sarebbe la ricerca Google News generica (`search_site()`), non verificata dal vivo in questo audit per
targeting sr-Latn/cirillico o filtro geografico — e comunque erediterebbe lo stesso limite gia' misurato
per GDELT (vedi `docs/SOURCE_AUDIT.csv`, riga `GDELT_DOC2`): query broad su "Balcani" tendono a pescare
Federazione/Sarajevo/regione, non specificamente RS, che e' il vero gap di questo progetto.

**Verdetto**: **REJECT**. Costo di dipendenze (viola il vincolo di progetto "solo 2") + fragilita' nota
del decoder Google (4 riscritture) + zero copertura RS/BiH dimostrata nel registro curato.

---

## 2. `fhamborg/news-please`

**Esiste**: si — 2485 star, Apache-2.0, attivo (ultimo push 2026-04-14), progetto maturo (dal 2016).

**Cosa fa**: crawler generico (Scrapy + newspaper4k + readability), estrazione articolo con piu' fallback,
CLI + libreria + archivio commoncrawl.org.

**Dipendenze reali** (`requirements.txt` letto dal vivo, 22 righe): `Scrapy, PyMySQL, psycopg2-binary,
hjson, elasticsearch, beautifulsoup4, readability-lxml, langdetect, python-dateutil, plac, dotmap,
PyDispatcher, warcio, ago, six, hurry.filesize, bs4, faust-cchardet, boto3, redis, newspaper4k,
lxml-html-clean, typing-extensions`. Include driver Postgres (`psycopg2-binary`), MySQL (`PyMySQL`),
Elasticsearch, Redis, boto3 (AWS) **incondizionati nel requirements.txt di base**, non come extra
opzionali — un ordine di grandezza oltre quello che questo progetto usa in tutto (`sqlite3`+stdlib).

**RS/BiH fit**: nessuna copertura pre-configurata, e' un crawler generico che va puntato manualmente su
URL — non aggiunge FONTI nuove di per se', solo un motore di estrazione alternativo a `trafilatura` (gia'
in uso e funzionante, nessun problema di estrazione misurato che lo richieda).

**Verdetto**: **REJECT**. Non aggiunge copertura (serve solo come estrattore, ridondante con
`trafilatura` gia' operativo), overengineering enorme sul lato dipendenze (DB driver multipli, cloud SDK)
per un progetto che vieta esplicitamente database ed e' a 2 dipendenze.

---

## 3. `RSS-Bridge/rss-bridge`

**Esiste**: si — 9192 star, Unlicense, PHP, molto attivo (ultimo push 2026-08-28, ieri). Il piu' maturo dei
6.

**Cosa fa**: genera feed RSS per siti che non ne hanno, tramite "Bridges" (uno scraper dedicato per sito,
549 bridge totali nel repo). Richiede di far girare un'istanza PHP (server web), non e' una libreria
Python importabile.

**Verifica esplicitamente richiesta dalla task**: "non assumere che esistano bridge come
`Banjaluka24Bridge`/`RTRSBridge`". Verificato dal vivo: `gh api repos/RSS-Bridge/rss-bridge/contents/bridges`
→ **549 file, zero bridge per domini Bosnia/Serbia/Balcani** (grep su `bosn|serb|balkan|rtrs|banjaluka|
klix|glassrpske|nezavisne|n1info` = 0 match reali, l'unico hit del grep — `FurAffinityUserBridge.php` — e'
un falso positivo del pattern, non un sito Balcani). **Confermato: nessun `Banjaluka24Bridge`,
`RTRSBridge`, o equivalente esiste.** Costruirne uno da zero non e' "usare un provider esterno", e'
scrivere uno scraper dedicato — esattamente il "bridge custom per Banjaluka24" che la task vieta
esplicitamente (§4, gia' risolto in `TASK_BETA_03_RESULTS.md` D0.1) e l'equivalente per RTRS che
richiederebbe di reinventare cio' che il nostro `collect.py` gia' fa via RSS diretto.

**Costo operativo**: richiederebbe di installare e far girare un servizio PHP separato (§2 vieta
esplicitamente "microservizi"/framework nuovi) solo per ottenere feed su siti gia' coperti direttamente.

**Verdetto**: **REJECT**. Nessuna copertura RS/BiH reale nel catalogo esistente; costruire bridge nuovi
e' fuori scope (equivale a scrivere scraper custom); richiede un servizio PHP separato per un progetto
Python "niente microservizi".

---

## 4. `viperdam/zero-cost-news-scraper`

**Esiste**: si, ma — 0 star, 0 fork, **5 commit totali, tutti nello stesso giorno** (2025-08-03, dalle
09:25 alle 21:04 UTC) e **nessun commit da oltre un anno** (`pushed_at: 2025-08-03T21:04:30Z` vs oggi
2026-08-29). Progetto abbandonato dopo un singolo giorno di sviluppo.

**Cosa dichiara**: pipeline "zero-cost" con Scrapy + FastAPI + **PostgreSQL (Neon)** + GitHub Actions.
Il README stesso riporta lo stato reale al momento dell'ultimo commit: **"Database: 4 articoli
salvati"** — quattro, in totale, mai piu' aggiornato.

**Perche' REJECT immediato, indipendente dal resto**: richiede un database Postgres esterno per
funzionare. `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md` §2 vieta esplicitamente
"non introdurre database" — questo candidato lo richiede nel suo design stesso, non come opzione.

**Verdetto**: **REJECT**. Database obbligatorio (vietato dalla task), progetto abbandonato da 1+ anno,
4 articoli mai raccolti in totale, zero evidenza di copertura di qualunque tipo, tanto meno RS/BiH.

---

## 5. `riad-azz/next-news-api`

**Esiste**: si — TypeScript/Next.js, MIT, 30 star, ma **ultimo push 2024-06-27** (oltre 2 anni fa,
sostanzialmente fermo).

**Cosa fa**: applicazione web Next.js deployata su Vercel che espone `/api/news` leggendo un elenco
fisso di feed RSS hardcoded in `src/lib/news/constants.ts` (letto dal vivo). **Elenco fonti verificato
dal vivo**: Yahoo News, Life Hacker, New York Times, CNN, Huffington Post, Fox News, Reuters, Politico,
LA Times, poi una lunga serie di fonti australiane (Sydney Morning Herald, ABC News, The Age, ecc.) —
**zero fonti Bosnia/Serbia/Balcani**, tutte fonti anglofone USA/Australia.

**Mismatch architetturale**: e' un'app Next.js/Node da buildare e deployare (`npm install && npm run
build`), non una libreria Python — introdurla significherebbe aggiungere un secondo runtime/framework
al progetto, vietato esplicitamente (§2 "non creare framework plugin").

**Verdetto**: **REJECT**. Zero fonti RS/BiH nell'elenco reale (verificato, non l'elenco completo ma
un campione ampio sufficiente a escludere qualunque copertura Balcani), progetto fermo da 2+ anni,
runtime incompatibile (Node/Next.js) con una pipeline Python a 2 dipendenze.

---

## 6. `jasonforis/mediafilter-auto-parse`

**Esiste**: si, ma — **non e' uno scraper**. Contenuto reale (letto README + contenuti root dal vivo): un
singolo GitHub Actions workflow che ogni 15 minuti fa una POST a
`https://base44-68e7c6e54ddaf4cef5af343a.deno.dev/cronParseRSS`, un endpoint privato di un progetto terzo
non correlato ("MediaFilter", 30 fonti russe + 10 internazionali secondo la descrizione, nessun codice di
parsing visibile in questo repository — vive interamente sul backend Deno privato, non ispezionabile).

**MISMATCH**: non c'e' nulla da integrare — nessuna libreria, nessun bridge, nessun parser riusabile.
E' un cron-trigger per un servizio privato altrui, in russo, senza relazione con RS/BiH.

**Verdetto**: **REJECT** (mismatch — non e' uno scraper utilizzabile, non un semplice "no" su copertura).

---

## Tabella riepilogo

| candidato | esiste | ultimo commit | licenza | runtime | dipendenze nuove | RS/BiH reale | verdetto |
|---|---|---|---|---|---:|---|---|
| open-news | si | 2026-06-29 | MIT | Python | 6-7 (+ transitive) | 0 (registro verificato) | REJECT |
| news-please | si | 2026-04-14 | Apache-2.0 | Python | 22 (incl. Postgres/MySQL/ES/Redis/boto3) | 0 | REJECT |
| RSS-Bridge | si | 2026-08-28 | Unlicense | **PHP** | servizio separato | 0/549 bridge (verificato) | REJECT |
| zero-cost-news-scraper | si (abbandonato 1+ anno) | 2025-08-03 | MIT | Python | Scrapy+FastAPI+**Postgres** | 0 (4 articoli totali mai) | REJECT |
| next-news-api | si (fermo 2+ anni) | 2024-06-27 | MIT | **Node/TS** | framework intero | 0 (elenco verificato) | REJECT |
| mediafilter-auto-parse | si (non e' uno scraper) | 2025-10-12 | — | — | n/a | n/a | REJECT (mismatch) |

## Motivazione aggregata

Nessuno dei 6 supera anche solo UNO dei vincoli hard gia' stabiliti per questo progetto
(`docs/TASK_SCRAPER_PILOT.md` §VINCOLI HARD, mai revocati): 2 dipendenze totali, niente database, niente
framework/microservizi nuovi. Quattro (`news-please`, `zero-cost-news-scraper`, `RSS-Bridge`,
`next-news-api`) li violano nel design stesso (DB obbligatorio, runtime alternativo, o decine di
dipendenze). Uno (`mediafilter-auto-parse`) non e' uno scraper utilizzabile. L'unico con un angolo di
reale novita' tecnica (`open-news`, decodifica Google News) porta comunque zero copertura RS/BiH
verificata nel suo registro curato, e il suo unico meccanismo potenzialmente utile (ricerca Google News)
eredita lo stesso limite geografico gia' misurato e scartato per GDELT (`docs/SOURCE_AUDIT.csv`), a un
costo di dipendenze che nessuno dei precedenti scarti aveva mai accettato.

**§26 — classificazione finale**: tutti e 6 **REJECT**. Nessun `KEEP`/`DISCOVERY_ONLY`/`FALLBACK_ONLY`.
Adapter, pilot, config e test di BLOCCO A non costruiti di conseguenza (la task lo permette esplicitamente
come esito legittimo — vedi §3: "non scegliere il provider piu' facile", "non forzare una scelta debole").
