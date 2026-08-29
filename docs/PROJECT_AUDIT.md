# MEDIA PILOT / RADAR POLITICO — PROJECT AUDIT (Fase 0)

Data audit: 2026-08-27
Ambito ispezionato: `C:\Users\frontofficedx\Desktop\NIK 2026\` (US/, IZVORI/, radice)
Output richiesto dal master prompt §103: sezioni A–K. **Nessun file di implementazione prodotto.**

Copia canonica assunta: `US/________media-pilot-v21-2026-08-26/media-pilot-v21-simple/`
Motivo: mtime più recente (2026-08-26 06:18) ed è l'unica con `RECENT_UPDATE_2026-08-26.md`.
`US/media-pilot-v21/` e `US/media-pilot-v21-orb/` sono trattate come superate (differiscono solo per
README/app.css/ui.js e per seed dati più vecchi). Assunzione risolta da mtime, non domanda bloccante.

---

## A. CURRENT STATE

### A.1 Repository — non esiste
`find … -name .git` su tutto `NIK 2026` → **zero risultati**. Non c'è versionamento.
Il versionamento oggi è per copia di cartella: ~20 generazioni (`v14 … v21`) più gli zip corrispondenti,
di cui 3 copie quasi identiche della sola v21. §60/§68/§82 (sicurezza, versionamento, backup) sono
inapplicabili finché non esiste un repo.

### A.2 Frontend (funzionante, non demo morta)
Vanilla HTML/CSS/JS, nessun framework, nessun CDN, nessun build step a runtime. Struttura piatta:

| File | Ruolo |
|---|---|
| `index.html` `us.html` `konkurenti.html` `ostali.html` `vrh.html` `media.html` `eksperti.html` `go.html` `case.html` `arhiva.html` `simulator.html` | gusci da ~20 righe, un `<div id="app">` + script |
| `data.js` | caricamento dati, memoizzato, con **switch `mode:'local' \| 'api'` già presente** |
| `store.js` | stato in localStorage prefisso `mp_v21:` — role, operator, cases, tasks, blackbox (max 800), seen |
| `radar.js` | **RadarEngine** — funzioni pure, zero DOM, UMD (browser + Node) |
| `dashboard-config.js` | definizione dichiarativa delle card |
| `ui.js` `header.js` `page-*.js` | rendering |
| `tools/build-data.js` | generatore Node dei JSON + `embedded-data.js` |
| `_selftest.html` | autotest in pagina |
| `assets/data/*.json` | 8 file (rassegna 206KB, trending 108KB, cases 66KB, archive 63KB, candidates 40KB, signals 37KB, tasks 17KB, alerts 15KB) |
| `embedded-data.js` | 584KB, fallback per apertura via `file://` |

### A.3 RadarEngine — la catena esiste già ed è deterministica
`radar.js` implementa integralmente la pipeline RASSEGNA→TRENDING→SIGNAL→ALERT→CASE con soglie
esplicite e commentate, **senza alcun LLM**. È già la condizione §97 "funziona senza LLM".

```
rassegna : menu ∈ {news, social, local, institutions, campaign}, dedup per titolo normalizzato
trending : velocity ≥ 4 item che condividono ≥ 2 moduli, OPPURE source jump (locale↔nazionale)
signals  : ≥ 3 hit su POLITICAL_MODULES
alerts   : risk_score ≥ 3.5 OR cross-reference (≥2 SENSITIVE_MODULES) OR signal_to_vrh
cases    : create_case === true OR (risk_score ≥ 4.0 AND human_review === true)
priority : risk_score ≥5 → P1, ≥4 → P2, altrimenti P3
```

Espone inoltre `themeStatus()` (8 semafori tematici), `cardItems/cardStatus/rankCards` (semafori card),
`datasetNow()` (il "now" è la data massima del dataset, non `Date.now()`).
`themeStatus()` restituisce già `sources[]` con `url: null` e il commento *"lo scraper non fornisce ancora
url reali: mai inventarli"* — la disciplina §101 è già nel codice.

### A.4 Card contract — già dichiarativo
`dashboard-config.js` definisce 54 card in 4 gruppi: **US 15, KONKURENTI 15, OSTALI 12, TERITORIJ 12**.
Ogni card è una query stabile: `{key, label, meta, keywords[], modules[], ij, type, base, theme, mark}`
con `type ∈ {actor, party, relation, territory, race, institution, model, external}`.
`RadarEngine.cardStatus()` ne calcola livello (red/orange/blue/green), count24/count7, trend, maxRisk,
hasCase/hasAlert, top item e `weight` per il riordino. L'ordine base è stabile; solo alert/case/trend promuovono.

### A.5 Dati — 100% autoriali (seed), zero raccolti
`tools/build-data.js` legge da:
- `…\_____us-demo-media-pilot-v19-large-light\…\scenarios.json` — **160 scenari scritti a mano** (8 menu × 20)
- `archive_cases.json` (stessa cartella v19)
- `assets/data/candidates_source.json` (scritto a mano in questo repo)

e genera nella stessa esecuzione i JSON e `embedded-data.js` dagli **stessi oggetti** (non possono divergere).
Task e case sono derivati deterministicamente (hash dell'id, nessun `Math.random`).
`RECENT_UPDATE_2026-08-26.md` documenta il seed politico allineato alle liste CIK 19–25.08.2026 e ne dichiara le fonti.

`candidates_source.json` è l'unico posto dove esiste già il pattern evidence corretto:
ogni candidato ha `source_url`, `source_name`, `fetched_at`.

### A.6 Prototipi backend — orfani
In `US/` (sciolti, non in una cartella, datati 2026-04-24):
`backend_models_fastapi.py` (18KB, Pydantic + enum), `backend_models_sqlalchemy.py` (19KB),
`backend_schema.sql` (11KB, DDL PostgreSQL con `sources`/`raw_items`/…), `backend_scoring_service.py` (26KB).
Non sono collegati a nulla, non hanno `requirements.txt`, non sono importati da nessun file.
**Vocabolario divergente** dal v21: enum in serbo (`Relevance`, `Novelty`, `SourceType`, `SourceCategory`),
mappe di scoring 0–3, mentre `radar.js` usa `risk_score` 2–5. Vanno riconciliati, non riusati alla cieca.

### A.7 Registry fonti — esiste, ma nessuna fonte è verificata tecnicamente
Quattro generazioni di registry, tutte da **110 righe** (109 fonti + header):
`IZVORI_MASTER_media-pilot_FINAL-sa-sugestijama.csv` (il più ricco, 39 colonne),
`IZVORI/media_pilot_master_sources_v12_COMPATIBILISSIMO.csv`, `…glavni izvori_podijela…csv`,
`media_pilot_facebook_fonti_aggiornate_v14.csv`, più ~10 XLSX intermedi.

Distribuzione (IZVORI_MASTER, colonna `makro_tip`):
RS_MEDIA_LOKALNO 41 · MEDIA_PORTALI 16 · SRBIJA_HRVATSKA 15 · PARTIJE_POKRETI 13 · EKONOMIJA 10 ·
IZBORI_ONG_MONITORING 8 · FEDERACIJA_BIH 7.
`website_url` valorizzato in 108/110, `facebook_url` in 101/110.

**Non esiste alcuna colonna `feed_url` / `rss` / `api`.** La colonna `preferred_ingestion` di
`master_sources_v12` contiene stringhe come `"website/API/manual PDF"`, `"website/RSS/manual PDF"`:
sono **aspirazioni redazionali, non fatti verificati**. Nessuna riga è oggi `READY_RSS`.

### A.8 Segreti — nessuno presente
Grep su tutto `NIK 2026/US` + CSV + MD per `YOUTUBE_API_KEY|api_key|apikey|Bearer |AIza…|sk-…|ACCESS_TOKEN`:
**zero risultati**. Nessun `.env`, nessun `.env.example`, nessun token nel codice. (Verificato senza stampare valori.)
Nessun `requirements.txt`, `docker-compose*`, `*.yaml`, `*.yml` legato a Media Pilot.

### A.9 Documentazione di specifica già esistente
`US/MEDIA-PILOT-V20-TASKS.md` (32KB) contiene la specifica completa V20 e — importante — **dichiara già il
formato che lo scraper dovrà produrre**:

```json
{"source":"BN TV","url":"…","title":"…","text":"…","timestamp":"…","entities":["US","STE","OHR"],
 "territory":"IJ3","source_type":"national","bias":"opposition","duplicates":[],"cluster_id":"CL-2026-044"}
```

Il lavoro sul data contract è quindi **riconciliazione**, non invenzione.

---

## B. EXISTING ASSETS (da riusare, non riscrivere)

1. **`data.js` con `mode:'api'`** — lo switch e la mappa endpoint (`rassegna→/api/radar-feed`, `cases→/api/cases`,
   `tasks→/api/tasks`, `archive→/api/archive`) sono già scritti e commentati. Rende la Fase A/B di §52 quasi gratuita.
2. **`radar.js`** — signal engine deterministico, soglie isolate in cima al file, già condiviso browser/Node.
   È la cosa più preziosa del progetto: non va riscritta, va **alimentata**.
3. **`dashboard-config.js`** — 54 card come query dichiarative. È di fatto il card data contract di §44.
4. **`tools/build-data.js`** — è già la forma esatta dell'"emettitore JSON" che il backend dovrà sostituire
   in Fase A (§52): stesso set di 8 file, stessa serializzazione.
5. **Registry 110 fonti** con metadati ricchi (tier, pilot_score, election_relevance, ij_relevance,
   credibility, bias_score, technical_access…). Base pronta per `config/sources.yaml`, previa verifica tecnica.
6. **`candidates_source.json`** — pattern evidence (`source_url`/`source_name`/`fetched_at`) già in uso.
7. **`MEDIA-PILOT-V20-TASKS.md`** — formato scraper già dichiarato + regole UTF-8 senza BOM e escaping,
   con i diacritici serbi trattati come bug bloccante.
8. **`_selftest.html`** — c'è già una cultura di autotest in pagina su cui innestare i test di pipeline.

---

## C. LEGACY / DUPLICATION

| Elemento | Stato | Azione proposta |
|---|---|---|
| ~20 cartelle `us-demo-media-pilot-v14…v21` + zip | legacy | congelare in `_archive/`, non cancellare finché non c'è git |
| 3 copie v21 (`v21`, `v21-orb`, `v21-2026-08-26`) | duplicazione | canonica = `v21-2026-08-26/media-pilot-v21-simple`; le altre due in `_archive/` |
| `build-data.js` **path assoluto hardcoded** alla cartella v19 | bug di riproducibilità | la pipeline non gira su un'altra macchina. Va parametrizzato prima di qualunque automazione |
| `backend_*.py` (4 file, aprile 2026) | orfani, vocabolario divergente | riconciliare gli enum col modello v21 o scartarli esplicitamente. **Non importarli così come sono** |
| Registry fonti v5→v14 (~14 file CSV/XLSX) | generazioni sovrapposte, colonne diverse | eleggere `IZVORI_MASTER_…FINAL` come unica sorgente, il resto in `_archive/` |
| `gemini-code-*.html`, `media_pilot_demo_app.jsx`, `dahboard_1_gemini-code-*.html`, `demo_html_25_modules/`, `logika*/` | esperimenti morti | `_archive/` |
| `IJ_REMAP` in `build-data.js` + `IJ_NAMES` in `dashboard-config.js` | **geografia elettorale non verificata, incoerente** | vedi D.3 e J.1 |

---

## D. GAPS

### D.1 Componenti che semplicemente non esistono
Collector (RSS/HTML/API) · normalizer · deduplicazione · event clustering · entity registry con alias
cirillico/latino · database · API backend · scheduler · fetch policy (timeout/retry/ETag) · error handling
per fonte · monitoraggio tecnico dello scraper · `config/` esterna · golden dataset · test · git · backup ·
`.env.example` · cost control LLM.

### D.2 Il gap strutturale: gli item sono *scenario-shaped*, non *article-shaped*
Questa è la vera scoperta dell'audit. **La dashboard non è "in attesa di un feed": il suo modello dati
contiene giudizi editoriali che nessun collector può produrre.** La catena RadarEngine si aggancia
interamente a campi scritti a mano.

Campi attuali di un item, divisi in tre bucket:

**Bucket 1 — SCRAPEABILE (un collector li produce davvero)**
`date` → `published_at` · `title` · `summary` (da lead/estratto) · `developer_info.real_news_source` →
`source_id` · `developer_info.real_news_date`
Da aggiungere: **`url`, `final_url`, `language`, `script`, `content_hash`, `scraped_at`, `evidence[]`**.
⚠️ **Oggi non esiste nessun campo `url` in nessun item.** §31 (evidence first) è oggi impossibile.

**Bucket 2 — DERIVABILE DETERMINISTICAMENTE (regole, niente LLM)**
`modules[]` ← entity registry + alias matching cirillico/latino (US, STE, SNSD, OHR, CIK, NSRS, IJ, GO…)
`territory_raw` / `territory_ij` ← `config/territories.json` **verificato** (oggi non lo è, vedi D.3)
`menu` ← `source_type` del registry (media_portal→news, local_portal→local, official_*→institutions,
social→social, campagna→campaign)
`race` / `candidates[]` ← lookup per `unit` su `candidates_source.json`
`duplicates[]` / `cluster_id` ← dedup + event clustering

**Bucket 3 — EDITORIALE (nessun collector lo produce: serve provenance MODEL o ANALYST)**
`risk` · `opportunity` · `wedge` · `developer_info.risk_score` · `create_case` · `human_review` ·
`signal_to_vrh` · `signal_to_media` · `owner` / `route_owner` · `deadline` ·
`suggested_responses[]` · `user_info` · `public_response_blocked` · `go_feedback_required` ·
`work_order_default_recipient`

**Conseguenza operativa (§92/§101):** `risk_score` guida ALERT, CASE, `priority()` e il colore di ogni card.
Se in Fase 6 si sostituisce il seed con dati reali senza risolvere il bucket 3, il sistema deve *inventare*
un `risk_score` — esattamente l'allucinazione che §35/§101 vietano. La soluzione è in G.2.

Nota: il formato già dichiarato in `MEDIA-PILOT-V20-TASKS.md` include `bias:"opposition"` — §67 dice che
l'orientamento editoriale deve essere **configurazione umana**, mai assegnato dal modello. Il registry ha già
una colonna `bias_score`: quello è il posto giusto, non l'item.

### D.3 Geografia elettorale — §6 è già violato dal codice attuale
Coesistono **tre sistemi di numerazione IJ incoerenti**:

1. `build-data.js` → `IJ_REMAP = { 'IJ 2'→IJ3 Banja Luka, 'IJ 3'→IJ5 Doboj, 'IJ 4'→IJ6 Bijeljina, 'IJ 5'→IJ7 Zvornik }`
2. i dati stessi → un item ha `"territory": "IJ 5 – Zvornik"` che viene rimappato a `"territory_ij": "IJ7"`:
   l'etichetta grezza e il remap **non concordano** su quale numero sia Zvornik
3. `dashboard-config.js` → `IJ_NAMES` hardcoda tutte e 9 le IJ con i comuni
   (IJ1 Prijedor, IJ2 Gradiška/Laktaši/Prnjavor/Srbac, IJ3 Banja Luka, IJ4 Derventa/Brod/Modriča/Vukosavlje,
   IJ5 Doboj/Teslić/Petrovo/Stanari, IJ6 Bijeljina/Brčko, IJ7 Zvornik, IJ8 Istočno Sarajevo, IJ9 Hercegovina)
4. i CSV registry hanno una loro colonna `izborna_jedinica` / `ij_code`

Nessuna delle quattro è tracciata a una fonte ufficiale. Ogni `territory_ij` negli 8 JSON eredita questa incertezza.

**Trappola da evitare esplicitamente:** *non* seedare `config/territories.json` da `IJ_NAMES`. È comodo e
sembra autorevole, ma significherebbe riciclare geografia non verificata dentro la configurazione.
Si parte come da §6: `districts: []`, `verified_at: null`, `official_source: null`.

### D.4 Fonti — zero verificate
110 righe con `website_url` / `facebook_url` / `x_url` / `youtube_url` e **nessuna colonna feed**.
Il SOURCE AUDIT di §13 è un passaggio di rete reale, non una compilazione a tavolino. Tutte le righe partono `TO_VERIFY`.

---

## E. SOURCE & API AUDIT PLAN

### E.1 Audit fonti (110 righe) — `docs/SOURCE_AUDIT.csv`
Colonne: `source_id, name, url, rss_url, atom_url, api, html_ok, js_required, sitemap, robots_ok,
canonical_pattern, date_pattern, fulltext_in_html, amp_duplicate, paywall, update_freq, language, script,
tos_note, priority_tier, stato, checked_at`.
Stati ammessi: `READY_RSS · READY_API · READY_HTML · MANUAL_ONLY · BLOCKED · TO_VERIFY · NOT_USEFUL`.
**Tutte le righe iniziano `TO_VERIFY`.** Un `READY_*` si scrive solo dopo una richiesta HTTP riuscita
registrata in fixture.

Metodo, per riga, in quest'ordine (§14): `/rss`, `/feed`, `/rss.xml`, `/atom.xml` + `<link rel="alternate">`
nell'HTML → `/sitemap.xml` → server-rendered? (confronto testo con e senza JS) → `robots.txt` → canonical + data.
Ordine di lavorazione per `priority_tier` (tier 1 prima).

### E.2 API esterne — da riverificare sulla documentazione corrente prima di scrivere il connector (§105)

| Servizio | Ruolo previsto | Da verificare prima |
|---|---|---|
| RSS/Atom | canale primario | esistenza per fonte |
| YouTube Data API v3 | canali partiti/leader/media/istituzioni | quota buckets 2026, costo `search.list`, strategia channel→uploads→playlistItems |
| GDELT DOC 2.0 / Context 2.0 | **solo discovery e cross-check**, mai fonte di verità | formato, limiti, risoluzione publisher originale |
| Google News | solo discovery fallback | disponibilità, TOS, risoluzione URL originale |
| Meta Graph API | pagine autorizzate | permission, Page Public Content Access, App Review, retention, uso AI |
| X / Twitter | opzionale, fuori MVP | tier, costo, retention, redistribution |
| Telegram | fuori core | Bot API vs client API, TOS |
| Provider news commerciali | solo se RSS+HTML non coprono | coverage sr/Cyrillic/portali locali, costo, diritti AI |

Nessuna di queste va integrata prima che l'audit E.1 dimostri che RSS+HTML **non** copre abbastanza.

---

## F. MINIMAL ARCHITECTURE

```
config/sources.yaml · entities.yaml · territories.json · scoring.yaml
                      ↓
        Collectors (Python)  BaseCollector → RSSCollector | GenericHTMLCollector | YouTubeCollector
                      ↓  RawItem (schema unico, §25)
                 Normalizer   canonical URL, UTF-8/NFC, cirillico+latino preservati, date → UTC
                      ↓
                 Dedup        content_hash → titolo normalizzato → similarità + finestra temporale
                      ↓
              Event Cluster   articolo ≠ evento
                      ↓
        Entity / Territory    alias matching da entities.yaml + territories.json verificato
                      ↓
              PostgreSQL      (full-text nativo, niente Elasticsearch)
                      ↓
              Signal Engine   PORT del radar.js esistente, stesse soglie, stessi nomi
                      ↓
                FastAPI       /api/radar-feed, /api/cases, /api/tasks, /api/archive (+ resto §51)
                      ↓
       frontend v21 esistente (data.js: mode 'local' → 'api', una riga)
```

Stack: Python 3.12, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, httpx, feedparser, trafilatura,
BeautifulSoup4, APScheduler, pytest. Docker Compose (backend + postgres).
Fuori dall'MVP: Redis, Kafka, Elasticsearch, microservizi, riscritture frontend, GraphQL.

**Decisione da prendere una volta (H, Fase 2):** il Signal Engine è un port Python di `radar.js` oppure
`radar.js` resta l'unica implementazione e gira in Node come step della pipeline. Il port duplica logica
(rischio di divergenza, che `build-data.js` oggi evita apposta); tenere Node evita la duplicazione ma
aggiunge un runtime. Raccomandazione: **port Python con test di equivalenza sullo stesso fixture** —
il confronto è meccanico e vincola il port a non divergere.

---

## G. DATA CONTRACT PLAN

Deliverable: `docs/dashboard-data-contract.md` + `schemas/*.json` + `data/fixtures/`.
Ogni risposta API porta `schema_version`. Nessuno scraper prima che il contratto sia stabile (§85).

### G.1 Principio: additivo, non sostitutivo
Il frontend attuale **non deve cambiare** nelle fasi 0–6. Il contratto v1.0 è "gli 8 JSON esistenti, con i
campi esistenti", più i seguenti campi **aggiuntivi** che il frontend può ignorare finché non serve:

```
url, final_url, source_id, language, script, content_hash, scraped_at,
evidence: [{item_id, source_id, url, published_at, evidence_type}],
provenance: OFFICIAL | MEDIA | SOCIAL | MANUAL | MODEL | ANALYST,
confidence: 0.0–1.0,
schema_version, scoring_version, extractor_prompt_version
```

`url` + `evidence[]` sono l'**unica modifica frontend reale** dell'intero piano MVP: `themeStatus()` oggi
scrive `url: null` di proposito; quando il campo arriva, il popup può finalmente linkare la fonte (§31, §79).

### G.2 Il bucket 3 (campi editoriali) — come si risolve

| Campo | Provenance in produzione | Regola |
|---|---|---|
| `risk_score`, `risk`, `opportunity`, `wedge` | `ANALYST` se scritto da umano · `MODEL` + `confidence` se suggerito da LLM · **assente** altrimenti | mai un default numerico inventato |
| `create_case`, `human_review`, `signal_to_vrh` | `ANALYST` soltanto | un LLM non può settarli (§93) |
| `owner`, `route_owner`, `deadline`, `work_order_default_recipient` | regola di routing da config, provenance `MODEL`/config | §47 |
| `suggested_responses[]`, `user_info` | `MODEL`, sempre etichettato | mai presentato come `OFFICIAL` |

**Nuovo input del Signal Engine, deterministico, che sostituisce `risk_score` quando questo manca:**
un `signal_score` composto **solo** da metriche misurabili di §37/§39 —
`source_diversity`, `velocity` vs baseline, `source_jump`, `relation_change`, centralità US dell'entità,
`verification`, `organic_weight` — con i componenti visibili nel payload.
Guardrail §93: **un ALERT P1 non può nascere da un `risk_score` con provenance `MODEL`**; serve
`ANALYST` oppure la soglia deterministica su `signal_score` con conferma da fonti indipendenti.
Le soglie attuali (3.5 / 4.0 / 5.0) sono un punto di partenza da validare sul golden dataset, non verità.

### G.3 Riconciliazione col formato già dichiarato
`MEDIA-PILOT-V20-TASKS.md` promette `{source,url,title,text,timestamp,entities[],territory,source_type,
bias,duplicates[],cluster_id}`. Mapping: `entities[]` ≡ `modules[]` (stesso vocabolario di sigle),
`territory` ≡ `territory_ij`, `source_type` ≡ colonna del registry, `bias` **non va nell'item** ma resta
`bias_score` sulla fonte in `sources.yaml` (§67).

---

## H. PHASED IMPLEMENTATION PLAN

Ogni fase: **PLAN → IMPLEMENT → TEST → REPORT → CHECK**. Report con esito `DONE / PARTIAL / FAILED / NOT STARTED`.

| Fase | Contenuto | Definition of Done |
|---|---|---|
| **0 — Audit & repo** | `git init` sulla copia canonica · `.gitignore` · `.env.example` · legacy in `_archive/` · `docs/SOURCE_AUDIT.csv` (110 righe `TO_VERIFY`) · `docs/CURRENT_DATA_FLOW.md` · fix del path assoluto in `build-data.js` | repo esiste, prima commit, build-data gira da path relativo |
| **0b — Territori** | `config/territories.json` **vuoto** + verifica delle 9 IJ contro la definizione ufficiale CIK BiH 2026 | ogni IJ ha `official_source` + `verified_at`, oppure resta `verification:"pending"` |
| **1 — Data contract** | `docs/dashboard-data-contract.md`, schemi RawItem/NormalizedItem/Event/Signal/Alert/Case/Task/Card, fixtures | contratto congelato, `schema_version 1.0` |
| **2 — Registry + RSS** | `config/sources.yaml` (dalle sole righe `READY_RSS`) · scheduler · RSSCollector · normalizer · PostgreSQL · **3–5 fonti, non 50** | fetch stabile, retry, date corrette, canonical URL, nessun duplicato ovvio, log |
| **3 — HTML collectors** | solo le fonti senza RSS, una per volta, ognuna con fixture + parser + test | titolo/data/testo/canonical corretti su fixture, test di regressione |
| **4 — Dedup + cluster** | senza LLM: hash → titolo normalizzato → similarità → finestra temporale | copie eliminate, cluster misurati sul golden dataset, provenance mantenuta |
| **5 — Entity registry** | `config/entities.yaml` con alias latino+cirillico (US, Stevandić/Стевандић, SNSD, NSRS, OHR, CIK, opposizione, Beograd) | matching corretto su entrambi gli script, falsi positivi misurati |
| **6 — Dashboard feed** | backend genera gli **stessi 8 JSON** (§52 Fase A) → poi `data.js` `mode:'api'` (Fase B) | dashboard funziona con dati reali senza modifiche al frontend |
| **7 — Trend / Signal** | mentions, unique_events, source_diversity, velocity vs baseline, source_jump | valori riproducibili, zero LLM, test su dati storici |
| **8 — AI extraction** | solo ora l'LLM, dopo il filtro Layer 0 (§33) | output strutturato + validazione Pydantic + confidence + provenance `MODEL` + fallback `REVIEW` + cost tracking |
| **9 — Alert / Case** | guardrail §42/§93 | nessun P1 da opinione del modello, evidence visibile, override analista, audit, feedback falsi positivi |
| **10 — YouTube** | canali realmente utili, channel registry, quota monitor | video dedupati, video→event, evidence link |
| **11 — GDELT discovery** | solo per recuperare ciò che il registry perde | nessun doppione, publisher originale risolto, mai Case diretto, recall migliorato misurabile |
| **12 — Social** | Meta / X / Telegram valutati separatamente | se valore basso → **non implementare** |

---

## I. TEST PLAN

- **Unit**: normalizzazione URL · parsing date → UTC · alias entità latino/cirillico · `normTitle` · dedup ·
  content hash · soglie di scoring · `priority()` · routing task.
- **Parser fixtures**: per ogni fonte un HTML/RSS salvato + titolo/data/testo attesi. Correzione di parser ⇒ nuova fixture (regressione).
- **Pipeline**: 10 raw → normalizzati attesi → duplicati attesi → cluster attesi → signal atteso.
- **Equivalenza engine**: stesso fixture in `radar.js` (Node) e nel port Python → output identico. Blocca la divergenza descritta in F.
- **Contract**: ogni risposta API validata contro lo schema; `schema_version` presente.
- **Golden dataset**: 50–100 articoli/eventi verificati a mano, ognuno con duplicate sì/no, entità, territorio,
  cluster, rilevanza, signal atteso. Senza questo non si può dire "lo scraper funziona bene".
- **Metriche** (§64): source success rate · parse success rate · riduzione duplicati · precision clustering ·
  precision entità/territorio · false alert rate · missed alert rate · time-to-detection · latenza dashboard.
- **Frontend**: `_selftest.html` esistente resta verde a ogni fase.

---

## J. RISKS

**J.1 — Geografia elettorale non verificata (alto, già attivo).**
`IJ_REMAP` e `IJ_NAMES` sono entrambi **non verificati** e reciprocamente incoerenti (D.3). Ogni
`territory_ij` negli 8 JSON e ogni card `TERITORIJ` eredita l'incertezza. Un radar territoriale che sbaglia
IJ manda l'attenzione nel comune sbagliato. Mitigazione: `territories.json` vuoto, verifica CIK come
deliverable nominato di Fase 0b, `verification:"pending"` fino a prova.

**J.2 — Il bucket 3 forza l'invenzione (alto).** Se la Fase 6 sostituisce il seed senza risolvere G.2, i
colori dei semafori diventano numeri inventati. Mitigazione: `signal_score` deterministico + provenance
obbligatoria + guardrail P1.

**J.3 — Zero fonti verificate (medio-alto).** Il piano assume RSS; potrebbe emergere che gran parte dei
portali locali RS non ne ha. Mitigazione: l'audit E.1 precede la scelta dei collector; se `READY_RSS` è
troppo basso, la Fase 2 parte comunque con le 3–5 migliori e la Fase 3 si allarga.

**J.4 — Nessun git (medio).** 20 generazioni di cartelle, `build-data.js` con path assoluto: oggi non è
possibile fare rollback né riprodurre una build su un'altra macchina. Mitigazione: Fase 0.

**J.5 — Social/Meta (medio).** Il registry ha 101 URL Facebook: è facile leggerlo come "faremo scraping di
Facebook". Non è consentito (§21). Le fonti social non accessibili via API autorizzata restano
`fetch_mode: manual`.

**J.6 — Duplicazione della logica di scoring (medio).** Tre vocabolari coesistono: `radar.js` (risk_score
2–5), `backend_scoring_service.py` (mappe 0–3, enum serbi), `MEDIA-PILOT-V20-TASKS.md`. Senza una
riconciliazione esplicita in Fase 1 il backend e la dashboard divergeranno.

**J.7 — Timing elettorale (contesto).** Elezioni 4 ottobre 2026 (dato presente nei file del progetto).
Il tempo utile è ~5 settimane: motivo in più per non aggiungere nulla che non serva all'MVP.

---

## K. EXACT FILES TO CREATE OR MODIFY

### K.1 Da MODIFICARE (deliberatamente quasi vuota)

| File | Fase | Modifica |
|---|---|---|
| `tools/build-data.js` | 0 | sostituire il path assoluto `C:\…\v19-large-light` con path relativo/argomento CLI |
| `data.js` | 6b | una riga: `mode: 'local'` → `'api'` (+ `apiEndpoints`). Già predisposto |
| `radar.js` | 7 | leggere le soglie da `config/scoring.yaml` invece che dalle costanti in testa (nessun cambio di logica) |
| `ui.js` / `page-*.js` | 6b | usare `evidence[].url` nei popup quando presente — oggi `url` è `null` di proposito |
| `dashboard-config.js` | 0b | `IJ_NAMES` → letto da `config/territories.json` dopo la verifica CIK |

**Nessun'altra modifica al frontend nelle fasi 0–6.** Le pagine, il CSS e lo store restano invariati.

### K.2 Da CREARE — Fase 0 (documentazione, zero codice applicativo)
```
.git/                                git init
.gitignore                           esclude .env, __pycache__, node_modules, *.zip
.env.example                         nomi variabili, MAI valori
docs/PROJECT_AUDIT.md                questo file
docs/SOURCE_AUDIT.csv                110 righe, tutte TO_VERIFY
docs/CURRENT_DATA_FLOW.md            scenarios.json → build-data.js → 8 JSON → radar.js → card
docs/GAPS.md                         estratto operativo della sezione D
_archive/                            v14…v20, copie v21 superate, registry vecchi, demo morte
```

### K.3 Da CREARE — Fase 0b/1 (config e contratto)
```
config/territories.json    districts: [], verified_at: null, official_source: null   ← MAI seedato da IJ_NAMES
config/sources.yaml        generato dalle sole righe READY_* del SOURCE_AUDIT
config/entities.yaml       US, STE, SNSD, NSRS, OHR, CIK, OPP, BEO + alias latino/cirillico
config/scoring.yaml        soglie oggi in radar.js, esternalizzate
docs/dashboard-data-contract.md      schema_version 1.0
schemas/{raw_item,normalized_item,event,signal,alert,case,task,card}.schema.json
data/fixtures/                       fixture per i test di pipeline
data/golden/golden_dataset.json      50–100 item verificati a mano
```

### K.4 Da CREARE — Fase 2+ (backend, solo dopo contratto approvato)
```
backend/app/main.py
backend/app/{api,models,schemas,services,collectors,normalization,dedup,extraction,scoring,archive}/
backend/tests/
backend/alembic/
requirements.txt
docker-compose.yml
```

### K.5 Da DECIDERE prima della Fase 2
Riuso o scarto di `backend_models_fastapi.py` / `backend_models_sqlalchemy.py` / `backend_schema.sql` /
`backend_scoring_service.py`. Contengono già `sources`/`raw_items` in DDL PostgreSQL: utili come base,
ma con vocabolario divergente. Vanno riconciliati col contratto di Fase 1 o scartati esplicitamente,
non importati alla cieca.

---

## DOMANDE BLOCCANTI

Nessuna blocca la stesura di questo audit né le Fasi 0–1. Due lo diventano più avanti:

1. **Fonte ufficiale per le 9 IJ 2026** (blocca la Fase 0b e ogni card territoriale).
   Serve il documento CIK BiH che definisce le circoscrizioni NSRS 2026 — non una deduzione dai dati esistenti.
2. **Chi autorizza `risk_score` / `create_case` / `signal_to_vrh` quando il seed viene sostituito?**
   (blocca la Fase 9). Se la risposta è "l'analista", serve un'interfaccia di scrittura; se è "il modello",
   servono i guardrail di G.2 prima di attivare gli alert.

Tutto il resto è verificabile direttamente nei file.
