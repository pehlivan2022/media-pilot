# TASK — Pipeline di ingestione (fonti → corpus interrogabile)

Prompt per Claude Code. Leggere tutto prima di scrivere una riga.

## SCOPE

**Solo la pipeline.** Fonti, raccolta, pulizia, dedup, clustering, assegnazione valore, RAG.

**Fuori scope, non toccare:** dashboard, `assets/data/*.json`, `embedded-data.js`, `data.js`,
`radar.js`, qualunque file HTML/CSS/JS del frontend. Il collegamento alla dashboard è un task successivo.

Output di questo task: un **corpus pulito e interrogabile** più una CLI per ispezionarlo.
Se alla fine si può fare `python -m pilot.ask "..."` e ottenere risposte con le fonti in fondo,
il task è riuscito. Il resto viene dopo.

Test su **10 fonti**, finestra **7 giorni**, **tutti i protagonisti** del radar.

## VINCOLI HARD

- **No overengineering.** Niente PostgreSQL, niente vector database, niente Elasticsearch,
  niente FastAPI, niente Docker, niente scheduler, niente framework di orchestrazione.
- **Dipendenze totali ammesse: 2** — `feedparser`, `trafilatura`. Tutto il resto è stdlib.
  Persistenza e ricerca: `sqlite3` con FTS5, che è già dentro Python. Niente SDK LLM: `urllib.request`.
- **Zero invenzione.** Niente RSS inventati, niente endpoint inventati, niente punteggi inventati,
  niente IJ dedotte. Se un dato non c'è: `null`.
- Tutto in **UTF-8 senza BOM**. Il testo originale non si traslittera mai. Le versioni normalizzate
  vivono in colonne separate e servono solo a cercare, mai a mostrare.

## PRIMA DI TUTTO

Leggere `docs/PROJECT_AUDIT.md`, sezioni **D.2** (i tre bucket di campi) e **D.3** (le IJ non verificate).
La sezione 5 di questo task è l'applicazione diretta di D.2: se si legge solo quella, si sbaglia.

---

## 1 — FONTI

Candidati: `C:\Users\frontofficedx\Desktop\NIK 2026\IZVORI_MASTER_media-pilot_FINAL-sa-sugestijama.csv`
Partire dalle righe `priority_tier = 1` con `election_relevance` alto.

Per ogni candidato, con una richiesta HTTP **reale**, in quest'ordine:

1. `<link rel="alternate" type="application/rss+xml">` nell'HTML della home
2. `/rss`, `/feed`, `/rss.xml`, `/atom.xml`, `/feed/`
3. `/sitemap.xml`, solo se ha `<lastmod>` recenti
4. HTML della sezione politica, solo se server-rendered (confronto: il testo c'è già senza eseguire JS?)

Fermarsi a **10 fonti** che restituiscono item degli ultimi 7 giorni. Provarne più di 10: molte non
avranno feed. Verificare anche `robots.txt` prima di usare il metodo 4.

`docs/SOURCE_AUDIT.csv` — una riga per **ogni** candidato provato, non solo per i 10 buoni:

```
source_id,name,url,feed_url,method,items_7d,fulltext_in_feed,robots_ok,stato,checked_at,note
```

`stato ∈ READY_RSS | READY_HTML | BLOCKED | NOT_USEFUL | TO_VERIFY`
Un `READY_*` si scrive **solo** dopo un fetch riuscito. Non copiare la colonna `preferred_ingestion`
del CSV di partenza: è un'aspirazione redazionale, non un fatto.

`config/sources.yaml`, generato solo dalle righe `READY_*`:

```yaml
- source_id: rtrs
  name: RTRS
  feed_url: null           # valorizzato solo se verificato
  fetch_mode: rss          # rss | html
  language: sr
  script: cyrl             # cyrl | latn | mixed
  source_type: media_public
  owner_group: null        # per l'indipendenza delle fonti, vedi §5
  territory: RS
  enabled: true
  last_verified_at: null
```

Se non si arriva a 10, **fermarsi e dichiarare quante sono**. Non riempire il numero con fonti non verificate.

---

## 2 — PROTAGONISTI

**Non scrivere a mano l'entity registry.** Generarlo da `dashboard-config.js`, che contiene già i 54
protagonisti con le loro keyword. Leggerlo, non modificarlo.

Per ogni card estrarre `key`, `label`, `keywords[]`, `modules[]`, `ij`, `type`.
Poi **aggiungere gli alias cirillici** con una tabella di traslitterazione deterministica
(`dž→џ, lj→љ, nj→њ, ć→ћ, č→ч, š→ш, ž→ж, đ→ђ` + il resto), applicata alle keyword latine.
Controllo: `Nenad Stevandić` deve produrre anche `Ненад Стевандић`.

Devono comparire nel registry generato: US, Nenad Stevandić, SNSD, i 9 nosioci IJ1–IJ9, Milan Petković,
SPS/Goran Selak, Škrebić, Jošić, Obren Petrović, SDS, Blanuša, Stanivuković, Trivić, Vukanović, CIK,
OHR, NSRS, Vijeće naroda, Savo Minić, Predsjedništvo BiH, Beograd.

Matching su un articolo: exact → alias → normalizzato senza diacritici → cirillico. **Niente fuzzy.**
Aggiungere una `stoplist` per gli alias corti e ambigui (`US`, `SP`, `NF`): richiedere il match su
parola intera e maiuscola, altrimenti generano falsi positivi ovunque.

---

## 3 — RACCOLTA

```
python -m pilot.collect --days 7
```

- finestra `now - 7d`, in UTC
- per fonte: timeout 15s, 2 retry con backoff, User-Agent identificabile, `If-None-Match`/`If-Modified-Since` se il server li dà
- una fonte che fallisce **non blocca le altre**: si logga e si continua
- append-only su `data/raw/YYYY-MM-DD.jsonl`, così una seconda run non riscarica e si può rilanciare tutto offline

RawItem, esattamente questi campi, niente di più:

```json
{"raw_id":"","source_id":"","url":"","final_url":"","title":"","author":null,
 "text":"","published_at":"","scraped_at":"","language":"","script":"",
 "http_status":200,"content_hash":""}
```

Nel raw non entra nulla di interpretativo: né rischio, né tono, né rilevanza.

Errori con stato esplicito, mai silenziosi: `FETCH_ERROR · PARSE_ERROR · EMPTY_CONTENT · RATE_LIMIT · BLOCKED`,
ognuno con timestamp, `source_id`, url, messaggio, retry count. In `data/errors.jsonl`.

---

## 4 — PULIZIA E NORMALIZZAZIONE

Testo pieno con `trafilatura` sulla pagina originale, solo se il feed non lo contiene già.

- via boilerplate: menu, "Podijeli", "Pročitajte još", blocchi correlati, banner cookie, firme ripetute
- `text_len < 200` → stato `EMPTY_CONTENT`, l'item non prosegue ma resta loggato
- canonical URL: via `utm_*`, `fbclid`, `gclid`, frammenti, varianti `?amp` e `/amp/`
- date → UTC, ISO 8601. **Distinguere `published_at` (l'articolo) da `occurred_at` (l'evento).**
  `occurred_at` resta `null` se non è esplicito nel testo: non dedurlo.
- `content_hash` = sha256 del testo normalizzato

**Cirillico e latino — la regola che rompe tutto se sbagliata:**
il testo originale non si tocca mai. In parallelo si salvano due colonne di servizio,
`title_norm` e `text_norm` = minuscolo + senza diacritici + cirillico convertito in latino.
Queste due servono **solo** a cercare e a fare matching. Non si mostrano, non si esportano,
non sostituiscono l'originale in nessun punto.

---

## 5 — DEDUP E CLUSTERING

Sono due cose diverse e vanno tenute separate.

**Dedup = stesso articolo.** In tre passaggi, in quest'ordine:
`content_hash` → titolo normalizzato identico → titolo molto simile entro 48h.
Il gruppo diventa **un** item con `duplicates[]` = gli altri url.
Un comunicato ripreso da 8 portali = 1 item con 8 evidence, non 8 item. Il rapporto va nel report.

**Clustering = stesso evento, articoli diversi.** Regole, niente LLM:
entità condivise + finestra temporale (48–72h) + sovrapposizione dei token di titolo sopra soglia.
La soglia va in `config/scoring.yaml` e **si calibra sul golden set**, non si sceglie a occhio.

```json
{"cluster_id":"","first_published_at":"","occurred_at":null,
 "items":[],"sources":[],"entities":[],"evidence_count":0}
```

Embedding **solo se** i test dimostrano che le regole non bastano. Criterio, non opinione:
precision o recall del clustering sotto 0.7 sul golden set.

---

## 6 — ASSEGNAZIONE VALORE

La parte più delicata. **Tre strati separati, che non si mescolano mai nello stesso oggetto.**

### Strato 1 — MISURATO (deterministico, ricavato solo dal corpus raccolto)

| Campo | Come si calcola |
|---|---|
| `n_copies` | quante fonti hanno ripreso il cluster |
| `source_diversity` | fonti **distinte e indipendenti** nel cluster — stesso `owner_group` conta una volta sola |
| `velocity` | item del cluster nelle ultime 4h / mediana attesa su baseline 7d. **Mai un valore assoluto senza baseline** |
| `source_jump` | il cluster nasce su fonte locale e arriva a nazionale o ufficiale |
| `novelty` | 1 − max similarità col corpus dei 30 giorni precedenti. Riciclo = novelty bassa |
| `entity_centrality` | per entità: nel titolo 1.0 · nel lead 0.6 · nel corpo 0.3 · assente 0 |
| `time_to_second_source` | quanto ci mette una seconda fonte indipendente a riprendere |
| `organic_weight` | penalizza copie identiche e crosspost. **Non significa "questo account è un bot"**: è solo un peso tecnico |

### Strato 2 — DERIVATO (regole deterministiche)

- `modules[]` ← entity registry. Nessun match → `[]`, e l'item resta fuori dai segnali.
- `menu` ← dal `source_type` della fonte: `media_*`→`news`, `local_*`→`local`, `official_*`→`institutions`, `party_*`→`campaign`
- `provenance` ← `OFFICIAL | MEDIA | SOCIAL | MANUAL`, dal registry della fonte
- `verification` ← `SINGLE_SOURCE | MULTI_SOURCE | OFFICIAL_CONFIRMED`, dal numero di fonti indipendenti
- `territory_raw` ← il testo trovato. **`territory_ij` resta `null`**: le IJ non sono verificate (audit D.3).
  Non dedurre l'IJ dal nome del comune, per quanto sembri ovvio.
- `evidence[]` ← `[{source_id, url, published_at, evidence_type:"article"}]` per l'originale e ogni duplicato

### Strato 3 — GIUDIZIO (mai un fatto)

Vive in un blocco **separato**, assente per default:

```json
"judgment": {"risk": null, "impact": null, "urgency": null, "note": null,
             "provenance": "MODEL", "confidence": 0.0,
             "model": "", "prompt_version": ""}
```

Campi che **non** si scrivono nell'item, mai, perché nessun collector può produrli (audit D.2, bucket 3):
`risk`, `opportunity`, `wedge`, `risk_score`, `create_case`, `human_review`, `signal_to_vrh`,
`signal_to_media`, `owner`, `deadline`, `suggested_responses`, `user_info`.

### `signal_score`

Somma pesata **dei soli campi dello strato 1**, con i pesi in `config/scoring.yaml` e i componenti
visibili nel payload, così ogni punteggio è ricostruibile:

```json
"signal_score": 2.7,
"components": {"source_diversity":0.8,"velocity":1.4,"source_jump":0,"novelty":0.9,"entity_centrality":1.0}
```

I pesi iniziali sono un punto di partenza da calibrare sul golden set, non una verità. Scrivere accanto
a ogni peso perché ha quel valore, oppure `# da calibrare`.

**Regola finale:** un `signal_score` alto è un invito a guardare, non un allarme. Il salto a P1/alert/case
non appartiene a questo task.

---

## 7 — RAG

Sul corpus raccolto, non su internet.

**Indice.** SQLite FTS5, tabella virtuale su `title_norm` e `text_norm` (le colonne di servizio del §4:
è ciò che rende cercabile un articolo cirillico digitando in latino). Colonne di filtro affiancate:
`source_id`, `published_at`, `cluster_id`, `entities`.
File unico `data/corpus.db`. Un `pilot/index.py` che ricostruisce l'indice da zero in un comando.

**Chunking.** Un articolo = un chunk. Si spezza solo sopra ~1500 caratteri, a paragrafo, con overlap
di una frase. Non chunkare articoli corti: si perde il contesto e non si guadagna niente.

**Retrieval.** BM25 di FTS5, top-k, più i filtri data ed entità.
**Un cluster conta come una voce**, non come 8 copie: altrimenti gli 8 portali che hanno ripreso lo stesso
comunicato occupano tutta la finestra di contesto e il resto sparisce.

**Risposta.**
```
python -m pilot.ask "što je Stevandić rekao o posebnoj sjednici NSRS?" --days 7
```
- con chiave LLM: sintesi breve, **ogni affermazione con `[1]`, `[2]`** mappati agli url in fondo
- senza chiave: stampa i passaggi trovati con url e data, senza sintesi
- in nessun caso una risposta senza url. Se il retrieval non trova niente: **"nessun documento nel corpus"**,
  non una risposta generata dalla conoscenza del modello

**Vector database: no.** Non finché non si misura che FTS5 non basta. Criterio: recall sul golden set
sotto 0.7 su query che un umano risolve leggendo il corpus. Solo allora, e solo embedding + cosine su
un file numpy, non un servizio.

---

## API

### Le due che ci sono
`.env` (mai committato, mai stampato) più `.env.example` coi soli nomi:

```
ANTHROPIC_API_KEY=
DEEPSEEK_API_KEY=
```

Una sola funzione `llm(prompt) -> str | None`, ~20 righe, `urllib.request`, niente SDK:
- Anthropic → `POST https://api.anthropic.com/v1/messages`
- DeepSeek → `POST https://api.deepseek.com/chat/completions` (OpenAI-compatible)
- provider da env; nessuna chiave presente → ritorna `None` e la pipeline continua

**Verificare model id e formato della richiesta sulla documentazione ufficiale prima di scrivere la chiamata.**
Non usare id ricordati a memoria.

L'LLM fa **due cose sole** in questo task:
1. `summary` quando il feed non dà né lead né descrizione
2. la sintesi finale di `pilot.ask`, con citazioni obbligatorie

Output sempre marcato `provenance: MODEL` con `confidence`. Mai usato per rischio, priorità, relazioni,
tono politico o clustering. **La pipeline deve girare completa con `.env` vuoto.**

### Le altre
GDELT, YouTube Data API, Google News, provider news commerciali: **non integrarle in questo task.**
Se una fonte del §1 sembra richiederle, aprire la documentazione ufficiale corrente, verificare
access level, quota, TOS, retention e uso AI, e **riportare l'esito nel report** — senza scrivere il connector.
Le API cambiano: non usare parametri, quote o endpoint ricordati.

---

## FILE

**Creare**
```
pilot/__init__.py
pilot/sources.py       audit fonti → docs/SOURCE_AUDIT.csv + config/sources.yaml
pilot/entities.py      dashboard-config.js → config/entities.yaml + alias cirillici
pilot/collect.py       fetch 7 giorni → data/raw/*.jsonl + data/errors.jsonl
pilot/clean.py         boilerplate, canonical url, date, hash, title_norm/text_norm
pilot/dedup.py         dedup + clustering
pilot/score.py         strato 1 e 2, signal_score, components
pilot/index.py         costruisce data/corpus.db (FTS5)
pilot/ask.py           retrieval + risposta con citazioni
pilot/llm.py           anthropic + deepseek, ~20 righe, opzionale
pilot/test_pipeline.py
config/sources.yaml
config/entities.yaml
config/scoring.yaml
docs/SOURCE_AUDIT.csv
.env.example
requirements.txt       feedparser, trafilatura
```

**Modificare:** niente. Nessun file esistente del progetto viene toccato.

---

## TEST

Un solo file, `pilot/test_pipeline.py`, `assert` puri:

1. canonical URL: `?utm_source=x#frag` e `/amp/` → stesso url pulito
2. tre formati di data diversi → stesso ISO UTC
3. `Ненад Стевандић` e `Nenad Stevandic` matchano la stessa entità
4. l'alias corto `US` non matcha dentro `plUS`, `USA`, `focus`
5. 3 copie dello stesso articolo → 1 item, 3 evidence
6. 3 articoli diversi sullo stesso evento → 1 cluster, 3 item
7. `source_diversity` non cresce se due fonti hanno lo stesso `owner_group`
8. nessun item in output contiene `risk_score`, `create_case` o `signal_to_vrh`
9. nessun item ha `territory_ij` valorizzato
10. il testo originale salvato conserva il cirillico; `text_norm` è latino
11. `ask` su una query senza risultati → "nessun documento nel corpus", non una risposta generata
12. `llm()` con env vuoto → `None`, e collect/clean/dedup/score/index finiscono comunque

Più i fixture: salvare RSS e HTML di 3 fonti in `data/fixtures/` e testare i parser offline.

**Golden set:** 30 articoli scelti a mano dal corpus raccolto, annotati con duplicate sì/no,
cluster atteso, entità attese. Serve a calibrare le soglie del §5 e a misurare il recall del §7.
Senza, non si può dire se la pipeline funziona: si può solo dire che gira.

## DEFINITION OF DONE

- [ ] `docs/SOURCE_AUDIT.csv` compilato per **ogni** candidato provato
- [ ] 10 fonti `READY_*` in `config/sources.yaml`, o il numero reale dichiarato
- [ ] `config/entities.yaml` generato, con cirillico, contiene tutti i protagonisti del §2
- [ ] `collect --days 7` gira; una fonte rotta non ferma le altre; errori in `data/errors.jsonl`
- [ ] dedup misurata: N raw → M item, rapporto nel report
- [ ] clustering misurato sul golden set: precision e recall dichiarate
- [ ] ogni item ha `evidence[]` con almeno un url. **Zero item senza url**
- [ ] `signal_score` presente con `components` visibili; nessun campo dello strato 3 scritto come fatto
- [ ] `data/corpus.db` costruito; `ask` risponde con citazioni; senza chiave stampa i passaggi
- [ ] `pytest` verde
- [ ] `.env` fuori dal repo, nessuna chiave nei log, nessun file del frontend modificato

## REPORT FINALE

Un solo report alla fine, non aggiornamenti intermedi. Esito per sezione:
`DONE / PARTIAL / FAILED / NOT STARTED`. Mai "dovrebbe funzionare" senza il test che lo dimostra.

Numeri richiesti:
- candidati provati / con feed trovato / usati
- raw scaricati → item dopo dedup → cluster (i due rapporti)
- item per fonte, e quali fonti hanno dato zero
- quanti item hanno matchato almeno un protagonista, quanti zero, e i 10 protagonisti più citati
- distribuzione di `signal_score` e i 5 cluster più alti, **con l'elenco dei componenti** che li hanno spinti
- 3 query di esempio su `ask`, con le risposte e le fonti citate
- API esterne verificate e loro esito, senza connector scritto
- cosa **non** ha funzionato: fonti perse, parser fragili, soglie ancora a occhio
