# MEDIA PILOT — PROSSIMI TASK DOPO BETA 02

**Data:** 2026-08-28  
**Stato di partenza:** TASK_BETA_02 chiuso  
**Scopo:** passare da una buona pipeline di raccolta a un vero **Radar politico-operativo**, senza overengineering e senza trasformare metriche tecniche in giudizi politici automatici.

## 0. Stato corrente da non rifare

Baseline finale misurata dopo `TASK_BETA_02`:

| stadio | stato |
|---|---:|
| raw raccolti | 2.027 |
| clean | 1.888 |
| dopo dedup | 1.614 |
| rilevanti | 592 |
| cluster | 396 |
| singoletti | 81,8% |
| `rassegna.json` | 592 item reali |
| item con card dashboard | 450 = 76% |
| valori distinti `signal_score` | 22 |
| test | 20/20 |

Già fatto: raccolta RSS/sitemap/Wayback, normalizzazione latino/cirillico, filtro temporale, dedup, clustering, matching entità, TF-IDF + coseno, soglie calibrate, bug dei gruppi dedup chiusi corretto, `novelty` tolta dal punteggio, `velocity` degradata a flag `trending_now`, exporter reale verso `assets/data/rassegna.json`, comando unico `python -m pilot.run_all`.

**Non riaprire queste parti solo per migliorare un numero.** In particolare: non continuare a cambiare i pesi per cercare 50+ valori distinti di `signal_score`.

## Principio architetturale

Il progetto PILOT_BIH definisce il flusso:

```text
RASSEGNA
  ↓
TRENDING
  ↓
SIGNAL
  ↓
ALERT
  ↓
CASE
  ↓
TASK / DECISION
  ↓
ARCHIVE
```

Regole:

```text
ARTICLE ≠ EVENT
EVENT ≠ SIGNAL
SIGNAL ≠ ALERT
ALERT ≠ CASE
CASE ≠ TASK
```

La Beta 02 ha lavorato soprattutto fino a **Rassegna/Eventi**. I prossimi task devono costruire progressivamente il resto del funnel.

# TASK BETA 03 — STABILIZZAZIONE + TRENDING REALE

## Obiettivo

Produrre il primo `trending.json` reale, basato su **entità + eventi + tempo**, non sul solo ranking dei cluster.

Questa è la priorità principale.

## D0 — Due debiti tecnici prima del Trending

### D0.1 — Correggere BL_IJ3_006 / Banjaluka24

Problema già misurato:
- `trafilatura` incorpora testo di articoli correlati;
- circa 71,4% degli item della fonte è contaminato;
- la contaminazione altera similarità e clustering.

Fare:
1. Isolare 15–20 URL della fonte.
2. Confrontare HTML originale, testo estratto attuale, titolo/articolo principale e blocchi correlati erroneamente incorporati.
3. Individuare una correzione **specifica della fonte**, minimale.
4. Non cambiare l'estrazione globale di tutte le fonti se non necessario.
5. Rigenerare pipeline.
6. Ricalcolare item dedup, cluster, singoletti e precisione sul campione Banjaluka24.
7. Eseguire test pipeline.

Done quando:
- almeno 90% del campione non contiene testo di articoli correlati;
- nessuna regressione sulle altre fonti;
- tutti i test verdi;
- risultato documentato.

### D0.2 — Completare il backfill già disponibile

Quattro fonti erano troncate da `MAX_BACKFILL_URLS=100`.

Fare:
- un altro giro **solo sulle fonti per cui il codice ha già dimostrato che esiste ulteriore storia**;
- non aggiungere nuovi scraper;
- non cambiare soglie di clustering;
- misurare giorni distinti per fonte, fonti attive/giorno, item nuovi, errori.

Per RTRS: audit breve su RSS/sitemap/Wayback. Se non emerge un metodo HTTP semplice e stabile, dichiarare il limite e continuare. Non costruire browser automation per recuperare storia.

Done quando:
- secondo giro misurato;
- mediana fonti attive/giorno aggiornata;
- nessun overengineering per forzare 30 giorni perfetti.

# D1 — TRENDING ENGINE PER ENTITÀ

Il vecchio `signal_score` ha poca granularità perché dipende troppo dai cluster. Il Radar deve anche rispondere a:

> Quale protagonista/tema sta crescendo rispetto al suo normale?

Questo non richiede che gli articoli siano nello stesso cluster.

## Unità del Trending

Calcolare trending per:
- persone;
- partiti;
- istituzioni;
- relazioni/card già verificate;
- temi solo se già presenti nel registry.

Niente nuove entità inventate automaticamente.

## Metriche minime per entità

Calcolare deterministicamente:

```text
mentions_1h
mentions_4h
mentions_24h
unique_events_4h
unique_events_24h
unique_sources_4h
unique_sources_24h
source_diversity_24h
acceleration
baseline_7d
share_of_voice_24h
last_event_at
```

`baseline_30d = null` finché la copertura storica non è sufficientemente larga e stabile.

## Actor / entity momentum

Aggiungere una misura relativa alla **baseline della stessa entità**, distinguendo volume assoluto da cambiamento rispetto al normale.

## Output

Produrre un output derivato, per esempio `data/trending_entities.jsonl`, e l'adapter dashboard `assets/data/trending.json`.

Prima di scegliere nomi/schema definitivi, leggere il formato reale di `assets/data/trending.json`.

**Non cambiare il frontend se l'adapter può rispettare lo schema esistente.**

Done quando ogni voce Trending può mostrare:
- entità/card;
- conteggi;
- variazione rispetto alla baseline;
- numero eventi;
- numero fonti;
- ultimo aggiornamento;
- top eventi;
- evidence URL.

# D2 — ENTITY SALIENCE E COPERTURA DELLE CARD

Problema: solo 450/592 item reali sono collegati a una card dashboard: **76%**.

Restano 9 card senza `modules` dichiarati:

```text
finansiranje
doboj
predsjednistvo
banjaluka
sps
sp-demos
dns-nps
josic
obren
```

## D2.1 — Audit card-per-card

Per ciascuna card creare una tabella con:

```text
card
label dashboard
entità già esistente?
alias già esistenti?
module/code già esistente?
evidenza nel config?
mapping sicuro?
azione
```

Azioni ammesse: `MAP`, `ADD_ENTITY`, `KEEP_NULL`, `REVIEW`.

**Non dedurre codici politici solo dal nome della card.**

## D2.2 — Entity salience

Non usare soltanto 4 livelli di `entity_centrality`.

Misurare indicatori osservabili:
- entità nel titolo;
- entità nel lead;
- numero occorrenze;
- numero entità protagoniste nello stesso evento;
- presenza come entità primaria del cluster/evento.

Produrre un valore più granulare ma auditabile. Non sostituire automaticamente il `signal_score` durante questo task: prima misurare distribuzione e utilità.

Done quando:
- le 9 card hanno una decisione esplicita;
- copertura card rimisurata;
- `entity_salience` documentata;
- nessun alias ambiguo introdotto senza test.

# TASK BETA 04 — SIGNAL ENGINE + CROSS-REFERENCE

Da iniziare **solo dopo** che Trending reale funziona.

## E1 — Signal Candidate

Un Signal non è “un articolo con score alto”.

Creare `SignalCandidate` da:
- Trending;
- eventi;
- source diversity;
- entity salience;
- freshness;
- cross-reference;
- verification;
- evidence.

Output iniziale: `MONITORING` / `REVIEW`.

Ogni Signal deve spiegare:

```text
why_now
entities
events
metrics
evidence
sources
first_seen
last_seen
provenance
confidence
```

Nessun testo AI è necessario per produrlo.

## E2 — Cross-reference Engine minimo

Riutilizzare prima ciò che esiste già:
- `config/crossrefs_seed_ids.json`;
- cross-reference legacy verificabili;
- relazioni già presenti nella dashboard.

Esempi storici del progetto:

```text
OHR ↔ NSRS ↔ STE
US ↔ REL ↔ OPPOZICIJA
BEOGRAD ↔ STE
CIK ↔ IZBORI 2026
```

Trattarli come configurazioni da verificare, non come fatti politici correnti.

Output tecnico iniziale: `KEEP`, `UPSHIFT`, `DOWNSHIFT`, `REVIEW`.

`OPEN_ALERT` e `OPEN_CASE_CANDIDATE` non devono creare automaticamente oggetti operativi persistenti.

## E3 — Relation change

Prima versione deterministica:
- co-occorrenza di due entità;
- numero eventi condivisi;
- numero fonti;
- variazione 24h vs baseline;
- relazione configurata sì/no.

Niente interpretazioni politiche qualitative senza evidenza strutturata o validazione umana.

## E4 — Dashboard Signals

Solo dopo E1-E3 generare `assets/data/signals.json` reale.

Ogni Signal deve aprire:

```text
Signal
→ perché è emerso
→ metriche
→ eventi
→ fonti
→ articoli
```

# TASK BETA 05 — ALERT GUARDRAILS + WORKFLOW UMANO

## F1 — Alert Candidate

Il sistema può proporre:

```text
MONITORING
P2_CANDIDATE
P1_CANDIDATE
REVIEW
```

ma un candidato P1 non deve diventare P1 operativo senza guardrail.

Controlli minimi:
- qualità/provenienza fonte;
- fonti indipendenti;
- evidence;
- entity certainty;
- territory certainty;
- verification;
- evento non duplicato;
- accelerazione reale;
- eventuale cross-reference verificato.

## F2 — Regola evidence-first

Nessun Alert senza:

```text
event_id
evidence[]
source_id
url
published_at
reason
provenance
```

Nessun Case senza evidence.

## F3 — Promozione umana

Flusso:

```text
Signal Candidate
→ Analista/Media review
→ Alert
→ eventuale Case
```

Azioni umane:

```text
APPROVE
DOWNGRADE
DISMISS
OPEN_CASE
```

con audit timestamp.

# TASK BETA 06 — CASE / TASK / DECISION / ARCHIVE

Non deve essere generato automaticamente dallo scraper.

## G1 — Separare Case da articolo/evento

Case = tema politico-operativo.

Minimo:

```text
case_id
title
status
priority
opened_by
created_at
updated_at
evidence[]
related_signals[]
human_summary
audit[]
```

`human_summary` e `model_summary` devono restare distinguibili.

## G2 — Task e routing

Routing consolidato:

```text
GO → MEDIA
GO → ANALISTA
MEDIA ↔ ANALISTA
MEDIA → VRH
ANALISTA → VRH
VRH → MEDIA
VRH → ANALISTA
GO ✕→ VRH
```

Task minimo:

```text
task_id
case_id
from_role
to_role
priority
status
title
note
created_at
updated_at
audit[]
```

## G3 — Archive

Archiviare events, signals, alerts, cases, decisions, tasks, evidence e timeline.

Obiettivo: poter ricostruire cosa si sapeva in quel momento e perché è stata presa una decisione.

# TASK BETA 07 — FONTI E COPERTURA SUCCESSIVA

Solo dopo che il funnel principale funziona.

## H1 — GDELT

Stato attuale: `VERIFICATO_NON_INTEGRATO`.

Usarlo eventualmente per discovery, cross-check, source jump e copertura esterna della RS. Non usarlo come fonte primaria e mai `GDELT → Case`.

## H2 — YouTube

Valutare solo canali ufficiali/pertinenti. Preferire API ufficiale e uploads playlist. Prima fare audit di canali e quota. Non implementare global search continuo.

## H3 — IJ / territorio

Oggi `territory_ij = null`, correttamente.

Task separato:
1. trovare fonte ufficiale;
2. costruire tabella comune/località → IJ;
3. citare fonte;
4. testare casi ambigui;
5. solo dopo attivare `territory_ij`.

Non derivare IJ da memoria politica o LLM.

# TASK BETA 08 — PASSAGGIO DA JSON STATICI AD API

**Non prioritario adesso.**

Fase A:
```text
pipeline → JSON statici generati automaticamente → dashboard esistente
```

Fase B futura:
```text
GET /api/rassegna
GET /api/trending
GET /api/signals
...
```

Fase C operativa: endpoint di scrittura per Case, Task, Decision, Review.

Non costruire backend/API prima che gli schema JSON reali siano stabili.

# Ordine consigliato

```text
BETA 03
  D0.1 fix Banjaluka24
  D0.2 secondo backfill
  D1 Trending per entità
  D2 card coverage + entity salience
        ↓ STOP + MISURA

BETA 04
  E1 Signal Candidate
  E2 Cross-reference
  E3 Relation change
  E4 signals.json reale
        ↓ STOP + TEST UMANO

BETA 05
  Alert Candidate + evidence guardrails + promozione umana
        ↓
BETA 06
  Case / Task / Decision / Archive
        ↓
BETA 07
  GDELT / YouTube / IJ / nuove fonti
        ↓
BETA 08
  API/backend solo se ormai necessario
```

# Cosa NON fare adesso

- non continuare a ottimizzare `signal_score` per ottenere più gradini;
- non reintrodurre `novelty` finché non esiste una baseline reale;
- non inventare ownership delle fonti;
- non assegnare IJ non verificate;
- non fare sentiment come score politico;
- non usare LLM per aprire P1/Case;
- non aggiungere Elasticsearch/vector DB/Kafka;
- non riscrivere la dashboard;
- non introdurre API/backend prima di stabilizzare i contratti JSON;
- non mescolare dati demo con dati reali senza marcarli;
- non trasformare i seed cross-reference in fatti politici senza verifica.

# Primo task da dare a Claude Code

```text
Leggi prima:
- docs/BETA_RESULTS.md
- docs/TASK_BETA_02_RESULTS.md
- docs/HANDOFF_PROGRESS.md
- docs/RFC_SECONDA_OPINIONE_02.md
- docs/MEDIA_SCRAPER_BUILD_GUIDE.md
- questo file

TASK: esegui SOLO TASK BETA 03, iniziando da D0.

Regole:
1. Non riaprire C1/C2/C3 di TASK_BETA_02 salvo regressione dimostrata.
2. Non cambiare i pesi di signal_score per aumentare artificialmente i valori distinti.
3. Prima correggi BL_IJ3_006/Banjaluka24 con un fix fonte-specifico e misurato.
4. Poi esegui il secondo giro di backfill solo sulle fonti già note come troncate.
5. Poi costruisci il Trending Engine PER ENTITÀ, non per solo cluster:
   mentions 1h/4h/24h, unique_events, unique_sources, acceleration,
   baseline_7d, share_of_voice, last_event_at.
6. baseline_30d resta null se i dati non la sostengono.
7. Ogni trending deve avere evidence e provenienza.
8. Rispetta lo schema reale di assets/data/trending.json: prima leggilo, poi crea l'adapter.
9. Non generare Alert, Case, Task o giudizi politici in questo task.
10. Fai audit delle 9 card senza modules, ma non inventare mapping.
11. Esegui i test dopo ogni fase.
12. Scrivi docs/TASK_BETA_03_RESULTS.md con PRIMA/DOPO e numeri reali.
13. FERMATI dopo BETA 03 e mostrami:
    - qualità Banjaluka24;
    - copertura storica;
    - distribuzione Trending;
    - top 20 entità per momentum;
    - copertura card;
    - test.

No overengineering. Zero invenzione. Dato non verificato = null.
```

# Definition of Done — BETA 03

- [ ] Banjaluka24 non contamina più sistematicamente il testo;
- [ ] backfill aggiuntivo misurato;
- [ ] `trending.json` contiene dati reali;
- [ ] trending è calcolato per entità;
- [ ] volume e momentum sono distinti;
- [ ] ogni trending ha eventi/fonti/evidence;
- [ ] baseline insufficiente produce `null`, non stime;
- [ ] le 9 card senza module hanno una decisione documentata;
- [ ] nessun Alert/Case inventato;
- [ ] pipeline completa ancora ripetibile;
- [ ] tutti i test verdi;
- [ ] `TASK_BETA_03_RESULTS.md` scritto;
- [ ] STOP prima di BETA 04.
