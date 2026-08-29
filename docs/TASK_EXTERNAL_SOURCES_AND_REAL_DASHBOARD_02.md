# TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02
## MEDIA PILOT / RADAR POLITICO — Più fonti reali + Dashboard senza simulazioni

**Stato:** READY_FOR_IMPLEMENTATION  
**Priorità:** IMMEDIATA DOPO `TASK_FINAL_DASHBOARD_BETA_01`  
**Scope:** DATA SOURCES + FRONTEND CLEANUP  
**Obiettivo:** aumentare la copertura reale delle fonti senza riscrivere la pipeline e rendere la dashboard operativa **100% basata su dati reali**, senza fallback silenziosi, card demo o sezioni simulate.

---

# 0. STATO DI PARTENZA — NON REGREDIRE

La Beta Dashboard è già implementata.

Risultati dichiarati dal task precedente:

- semafori derivati da `rassegna.json` + Signal `REVIEW`;
- rosso strutturalmente non raggiungibile automaticamente;
- 55/55 card reali;
- 0 rosse automatiche;
- HOME con:
  - pipeline status;
  - Trending Now;
  - Signal “Da gledati”;
  - Rassegna;
- sidebar collassabile desktop;
- drawer mobile esistente;
- `data.js` con isolamento per-file e `__missing[]`;
- niente fallback silenzioso globale verso demo;
- self-test Beta: **13/13 PASS**;
- documentazione aggiornata.

### Gap da chiudere
Verifica manuale responsive reale a:
- 390 px
- 768 px
- 1280 px
- 1920 px

Non riaprire la Beta salvo regressioni dimostrate.

---

# 1. OBIETTIVI DI QUESTO TASK

Il task ha due blocchi.

## BLOCCO A — FONTI REALI

Aumentare la copertura con **un solo provider esterno pilota**, mantenendo invariata la pipeline canonica:

```text
SOURCE / EXTERNAL PROVIDER
        ↓
adapter minimo
        ↓
RAW MEDIA PILOT
        ↓
clean
        ↓
entities
        ↓
dedup
        ↓
score
        ↓
trending
        ↓
signals
        ↓
dashboard
```

## BLOCCO B — ZERO SIMULAZIONI

La dashboard operativa non deve più presentare:
- dati demo;
- card inventate;
- fallback demo;
- Alert finti;
- Case finti;
- Task finti;
- Decision fittizie;
- numeri placeholder.

Se un modulo non ha ancora dati reali:

```text
NON MOSTRARLO
oppure
MOSTRARLO COME "IN SVILUPPO"
```

mai simularlo.

---

# 2. REGOLE NON NEGOZIABILI

## NON FARE

- non riscrivere `pilot/collect.py`;
- non riscrivere dedup/clustering/scoring;
- non cambiare TF-IDF;
- non modificare soglie Signal salvo bug;
- non creare framework plugin;
- non creare API backend;
- non introdurre database;
- non creare microservizi;
- non integrare più provider insieme;
- non aggiungere un secondo scraper prima di misurare il primo;
- non creare nuovi workflow Alert/Case/Task;
- non trasformare Signal in Alert automatici;
- non inventare fonti o mapping politici;
- non usare dati DEMO nella HOME operativa;
- non usare API key hardcodate;
- non versionare secrets.

---

# 3. AUDIT FONTI — PRIMA DI SCRIVERE CODICE

Creare:

```text
docs/EXTERNAL_SCRAPER_AUDIT_V2.md
```

Auditare realmente questi candidati:

1. `alphap365/open-news`
2. `fhamborg/news-please`
3. `RSS-Bridge/rss-bridge`
4. `viperdam/zero-cost-news-scraper`

Audit veloce aggiuntivo:
5. `riad-azz/next-news-api`
6. `jasonforis/mediafilter-auto-parse`

### Criteri

Per ogni repository verificare:

```text
repository exists
license
last meaningful commit
runtime
dependencies
original URL preserved
publish date quality
full text / summary
RSS discovery
search/discovery
RS/BiH usefulness
failure isolation
operational cost
```

### Regola fondamentale

Non scegliere il provider più facile.

Scegliere quello che produce la maggiore:

```text
COPERTURA INCREMENTALE REALE
```

per MEDIA PILOT.

---

# 4. AUDIT DELLE LACUNE REALI

Prima di scegliere il provider, creare:

```text
docs/SOURCE_GAPS_AUDIT.md
```

Identificare quali fonti/aree oggi sono deboli.

Per ciascuna:

```text
source_id
nome
problema
RSS disponibile?
storico sufficiente?
parser affidabile?
frequenza sufficiente?
articoli persi?
discovery insufficiente?
possible external helper
```

Categorie problema:

```text
NO_RSS
SHORT_HISTORY
BAD_EXTRACTION
DISCOVERY_GAP
INTERMITTENT_FAILURE
LOW_FREQUENCY
OTHER
```

### Non usare Banjaluka24 come problema automatico

Il problema contaminazione Banjaluka24 è già stato corretto.

Non creare un bridge custom per Banjaluka24 salvo nuova regressione dimostrata.

### RTRS

Se il problema è storico RSS corto:
- verificare se il provider esterno aggiunge realmente storico/copertura;
- se produce solo gli stessi articoli recenti → nessun valore.

---

# 5. SCELTA DEL SOLO PILOT

Selezionare **1 solo provider**.

Possibili ruoli:

## A. `open-news`
Possibile uso:
- RSS discovery;
- extraction fallback;
- Google News discovery;
- `search_site()`.

## B. `news-please`
Possibile uso:
- article extraction;
- crawling fallback.

## C. `RSS-Bridge`
Possibile uso:
- siti importanti senza RSS utile.

ATTENZIONE:
non assumere che esistano bridge come:

```text
Banjaluka24Bridge
RTRSBridge
```

Verificare realmente nel repository.

Se non esistono, NON inventarli in config.

## D. `zero-cost-news-scraper`
Possibile uso:
- discovery/RSS lightweight;
- solo se porta contenuti realmente nuovi.

---

# 6. CRITERIO DI SELEZIONE

Creare una tabella semplice.

Valutazione 0-2:

```text
license
maintenance
ease_of_install
provenance
original_url
date_quality
text_quality
incremental_coverage
RS_BiH_fit
failure_isolation
```

Il punteggio è solo orientativo.

### La decisione finale deve dipendere da:

1. nuovi articoli rilevanti;
2. nuovi domini utili;
3. nuovi eventi;
4. miglioramento tempestività;
5. affidabilità;
6. duplicazione;
7. costo operativo.

Non usare una soglia artificiale tipo `>14/20` come gate assoluto.

---

# 7. ADAPTER MINIMO

Solo dopo la scelta.

Creare:

```text
pilot/external/
    __init__.py
    <provider>_adapter.py
```

L'adapter deve:

- leggere il provider;
- mappare nel RAW schema reale MEDIA PILOT;
- preservare URL originale;
- preservare source/domain originale;
- preservare `published_at`;
- aggiungere provenance del provider;
- fallire senza bloccare la pipeline.

### Esempio concettuale

```json
{
  "source_id": "EXT_PROVIDER_001",
  "title": "...",
  "url": "https://original-domain/article",
  "published_at": "...",
  "text": "...",
  "original_domain": "original-domain",
  "external_provider": "provider_name",
  "provider_repository": "https://github.com/..."
}
```

Usare però i NOMI CAMPO REALI del progetto.

Non cambiare il RAW schema esistente per comodità.

---

# 8. SOURCE DIVERSITY

Regola obbligatoria.

Se un articolo arriva via:

```text
RSS-Bridge
Google News
open-news
news-please
```

il provider NON deve contare come fonte editoriale indipendente.

Esempio:

```text
provider = open-news
original_domain = rtrs.tv
```

Per `source_diversity`:

```text
rtrs.tv = 1 fonte
```

non:

```text
open-news + rtrs.tv = 2 fonti
```

---

# 9. CONFIGURAZIONE

Aggiungere il provider in `config/sources.yaml`.

Durante test:

```yaml
enabled: false
```

Attivarlo solo nel pilot.

Separare:

```text
provider_repository
provider_endpoint
original_article_url
original_domain
```

Nessun URL GitHub deve sostituire l'URL originale della notizia.

---

# 10. API COMMERCIALI / FREEMIUM

Non integrare NewsAPI / NewsData come fonte primaria in questo task.

Se vengono analizzate, creare:

```text
docs/EXTERNAL_API_AUDIT_V2.md
```

Verificare al momento:

```text
free tier
rate limit
delay
history
commercial/internal production use
API key
original URL
full text
```

Nessun dato hardcodato da vecchi audit.

---

# 11. TEST PILOTA

Eseguire un pilot breve.

Preferenza:

```text
24–72 ore
```

Se non è possibile eseguire 24–72h durante la sessione, preparare:
- config;
- logging;
- metriche;
- comando esatto;
- report iniziale;

e fare almeno smoke test reale.

Metriche:

```text
external_items_total
external_items_valid
external_items_duplicate
external_items_new
new_domains
new_relevant_items
new_events
new_entity_mentions
new_signal_candidates
errors
runtime
```

Confrontare:

```text
BASELINE
pipeline senza provider

vs

PILOT
pipeline + provider
```

---

# 12. DASHBOARD — ELIMINARE LE SIMULAZIONI

Auditare i frontend file reali:

```text
index.html
styles.css
app.js
radar.js
ui.js
data.js
dashboard-config.js
media.html
vrh.html
```

solo se presenti.

Cercare:

```text
demo
mock
fake
sample
fallback
placeholder
seed
static alerts
static cases
static tasks
static decisions
```

Creare:

```text
docs/DASHBOARD_REAL_DATA_AUDIT.md
```

Classificare ogni dataset/UI come:

```text
REAL
DEMO
MIXED
UNUSED
```

---

# 13. DATI REALI CANONICI

La dashboard operativa deve usare:

```text
assets/data/rassegna.json
assets/data/trending.json
assets/data/signals.json
data/pipeline_health.json
```

Se esistono altri JSON realmente generati dalla pipeline, documentarli.

### Regola

Il frontend NON deve generare una versione alternativa di Trending o Signals partendo da dati demo.

Il backend/Python resta canonico.

---

# 14. MODULI NON ANCORA REALI

Se:

```text
alerts.json
cases.json
tasks.json
archive.json
candidates.json
decisions.json
```

sono DEMO o incompleti:

### nella dashboard operativa

- rimuovere dalla HOME;
- non usarli per KPI;
- non usarli per semafori;
- non usarli per conteggi;
- non usarli per alert visuali.

Le pagine possono:

### Opzione preferita
essere nascoste dal menu operativo.

### Oppure
mostrare:

```text
Модул у развоју
Nessun dato operativo reale disponibile
```

senza numeri simulati.

---

# 15. VRH / CASE / ALERT DEMO

Il task precedente ha lasciato intatte le pagine demo.

Ora separare chiaramente:

```text
OPERATIVO
```

da:

```text
DEMO / DEV
```

Possibili soluzioni minime:

```text
?demo=1
```

oppure cartella:

```text
/demo/
```

oppure badge visibile:

```text
DEMO
```

### Preferenza

La navigazione utente normale non deve portare accidentalmente a dati simulati.

Non cancellare codice utile se serve ancora allo sviluppo.

Separarlo.

---

# 16. SEMAFORI — SOLO REALI

Conservare la logica Beta:

### GRIGIO
nessun dato / dati insufficienti.

### VERDE
attività normale.

### AMBRA
Signal `REVIEW` reale.

### ROSSO
solo Alert umano reale futuro.

### Divieto

Nessuna card rossa simulata.

Nessuna priorità demo.

Nessun `Math.random()` / rotazione finta / status hardcoded.

---

# 17. TRENDING — SOLO BACKEND

Usare solo:

```text
assets/data/trending.json
```

Non mantenere in parallelo un secondo algoritmo frontend se produce un ranking differente.

HOME:
massimo 5–8.

Dettaglio:
può mostrare tutti.

---

# 18. SIGNAL — SOLO BACKEND

Usare solo:

```text
assets/data/signals.json
```

HOME:
massimo 3–5 `REVIEW`.

MONITORING:
pagina dettaglio, se utile.

Nessun Signal demo.

---

# 19. RASSEGNA — SOLO REALE

`assets/data/rassegna.json`

Mostrare:
- titolo;
- fonte originale;
- ora/data;
- entità;
- link originale.

Nessun titolo demo quando il file è vuoto.

File vuoto:

```text
Nessuna notizia recente
```

File mancante:

```text
Dati non disponibili
```

---

# 20. HEALTH

`data/pipeline_health.json`

Deve alimentare lo stato sistema.

Esempio:

```text
ONLINE
DEGRADED
DATA UNAVAILABLE
```

Non simulare `ONLINE`.

Derivarlo realmente dal file health.

---

# 21. RESPONSIVE — CHIUDERE IL GAP BETA

Verificare manualmente / realmente:

```text
390
768
1280
1920
```

Per ciascuna larghezza verificare:

- sidebar/drawer;
- semafori;
- Trending;
- Signal;
- Rassegna;
- sheet/detail;
- no overflow;
- leggibilità.

Documentare risultato.

---

# 22. TEST DI NON REGRESSIONE

Tutti i test esistenti devono restare verdi.

Incluso:

```text
_selftest_beta.html
```

Atteso minimo:

```text
13/13 PASS
```

Aggiungere test per:

1. provider disabled = zero fetch;
2. errore provider isolato;
3. URL originale preservato;
4. dedup tra provider e fonte diretta;
5. provider non conta come fonte editoriale;
6. nessun fallback demo;
7. dataset DEMO non usato in HOME;
8. nessun rosso automatico;
9. missing JSON non rompe dashboard;
10. 390/768/1280/1920 senza overflow bloccante.

---

# 23. DOCUMENTI FINALI

Creare:

```text
docs/TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md
```

Includere:

```text
repository auditati
source gaps
provider selezionato
motivo
adapter creato
config modificata
metriche pilot
duplicati
copertura incrementale
nuovi domini
nuovi eventi
failure isolation
demo rimossi/separati
dataset operativi reali
responsive
test
limiti residui
```

Aggiornare:

```text
docs/FINAL_PROJECT_STATUS.md
docs/HANDOFF_PROGRESS.md
```

---

# 24. DEFINITION OF DONE

## Fonti

- [ ] source gaps audit completato;
- [ ] almeno 4 repository auditati realmente;
- [ ] scelto 1 solo provider;
- [ ] adapter minimo;
- [ ] provider disabilitabile;
- [ ] provenance preservata;
- [ ] URL originale preservato;
- [ ] source diversity corretta;
- [ ] error isolation;
- [ ] confronto baseline/pilot;
- [ ] copertura incrementale misurata.

## Dashboard

- [ ] nessun fallback demo silenzioso;
- [ ] nessun dato simulato in HOME;
- [ ] nessun KPI demo;
- [ ] nessun semaforo demo;
- [ ] nessun Alert/Case/Task finto mostrato come reale;
- [ ] pagine demo separate/nascoste/marcate;
- [ ] rassegna reale;
- [ ] trending reale;
- [ ] signals reali;
- [ ] health reale;
- [ ] responsive 390/768/1280/1920 verificato;
- [ ] `_selftest_beta.html` ancora verde;
- [ ] console senza errori bloccanti.

---

# 25. STOP CONDITION

Al termine:

**STOP.**

Non implementare il secondo provider.

Non costruire ancora:
- Alert workflow completo;
- Case;
- Task;
- Decision;
- Archive operativo.

Prima valutare il pilot e usare la dashboard reale.

---

# 26. DECISIONE FINALE PROVIDER

Classificare:

```text
KEEP
DISCOVERY_ONLY
FALLBACK_ONLY
REJECT
```

### KEEP
porta copertura incrementale utile e stabile.

### DISCOVERY_ONLY
utile per scoprire URL/fonti, ma non come source primario.

### FALLBACK_ONLY
utile quando il collector diretto fallisce.

### REJECT
troppo rumore, duplicazione o costo operativo.

---

# 27. ROADMAP DOPO QUESTO TASK

```text
BETA DASHBOARD          DONE
        ↓
EXTERNAL SOURCES + REAL DASHBOARD
        ↓
WINDOWS TASK SCHEDULER DEFINITIVO
        ↓
5–7 GIORNI LIVE
        ↓
TARATURA SIGNAL
        ↓
ALERT UMANO
        ↓
CASE / TASK / DECISION
        ↓
ARCHIVE
```

---

# 28. MODALITÀ CLAUDE CODE

Procedere:

```text
READ
→ AUDIT
→ SELECT ONE
→ IMPLEMENT MINIMAL
→ TEST
→ REMOVE/ISOLATE DEMO
→ RESPONSIVE CHECK
→ TEST
→ REPORT
→ STOP
```

Non chiedere conferma per micro-decisioni tecniche.

Se un dato non è verificabile:

```text
null
REVIEW
KEEP_NULL
```

Non inventare.

Non over-engineering.

---

# RISULTATO ATTESO

Alla fine di questo task:

1. MEDIA PILOT continua a funzionare con la pipeline attuale;
2. una sola integrazione esterna aggiunge copertura reale misurabile;
3. la dashboard operativa non mostra più simulazioni;
4. ogni notizia ha URL e fonte originale;
5. Trending e Signal arrivano solo dal backend reale;
6. i semafori derivano solo da dati reali;
7. moduli futuri non fingono di essere operativi;
8. il sistema resta semplice e disabilitabile/configurabile.
