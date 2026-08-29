# MEDIA PILOT / RADAR POLITICO — HANDOFF FINALE PER CONCLUDERE IL PROGETTO

**Data:** 2026-08-28  
**Scopo:** portare il progetto da beta tecnica a strumento operativo semplice, utile e programmabile.

---

# 1. OBIETTIVO FINALE

Il progetto deve fare tre cose bene:

1. **Raccogliere informazioni vere e aggiornate**
   - fonti media;
   - fonti istituzionali;
   - fonti locali;
   - eventuali fonti esterne di discovery;
   - solo dati verificabili.

2. **Aggiornarsi in modo programmabile**
   - decidere **cosa monitorare**;
   - decidere **quali fonti usare**;
   - decidere **quante volte al giorno aggiornare**;
   - permettere frequenze diverse per temi/fonti diverse.

3. **Alimentare una dashboard semplice e utile**
   - pochi elementi importanti;
   - semafori e Trending in primo piano;
   - ogni dato deve aprire le evidenze;
   - niente dashboard piena di numeri inutili.

Il prodotto finale non è “uno scraper”.

È:

```text
SCRAPER PROGRAMMABILE
        ↓
PIPELINE DATI
        ↓
EVENTI / TRENDING / SIGNAL
        ↓
DASHBOARD OPERATIVA
```

---

# 2. PRINCIPIO FONDAMENTALE

Il flusso concettuale del progetto resta:

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

Con queste regole:

```text
ARTICLE ≠ EVENT
EVENT ≠ SIGNAL
SIGNAL ≠ ALERT
ALERT ≠ CASE
CASE ≠ TASK
```

Non trasformare automaticamente una notizia in un allarme.

---

# 3. COSA ESISTE GIÀ

La pipeline Beta 02 è già funzionante.

Stato finale misurato:

| Stadio | Stato |
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

Già implementato:

- raccolta RSS;
- sitemap;
- Wayback CDX;
- normalizzazione;
- latino/cirillico;
- filtro temporale;
- canonical URL;
- hash;
- dedup;
- clustering;
- TF-IDF + coseno;
- entity matching;
- source diversity;
- `trending_now`;
- `source_jump`;
- export verso `assets/data/rassegna.json`;
- comando unico:

```bash
python -m pilot.run_all
```

e:

```bash
python -m pilot.run_all --no-collect
```

per rigenerare la pipeline usando i raw già presenti.

---

# 4. COSA NON VA PIÙ RIFATTO

Non perdere tempo a:

- riscrivere il dedup da zero;
- cambiare continuamente le soglie;
- inseguire 50+ valori distinti di `signal_score`;
- reintrodurre `novelty` senza storico sufficiente;
- cambiare tecnologia;
- introdurre vector DB;
- introdurre Elasticsearch;
- introdurre Kafka;
- creare microservizi;
- riscrivere il frontend.

Il progetto deve restare gestibile da una persona.

---

# 5. ARCHITETTURA FINALE MINIMA

```text
config/
  sources.yaml
  entities.yaml
  topics.yaml
  monitoring.yaml
  scoring.yaml

pilot/
  collect.py
  clean.py
  entities.py
  dedup.py
  score.py
  trending.py
  signals.py
  export_dashboard.py
  run_all.py

data/
  raw/
  clean.jsonl
  deduped.jsonl
  clusters.jsonl
  trending.jsonl
  signals.jsonl

assets/data/
  rassegna.json
  trending.json
  signals.json
  alerts.json
  cases.json
  tasks.json
  archive.json
  candidates.json

docs/
  SOURCE_AUDIT.csv
  dashboard-data-contract.md
  HANDOFF_PROGRESS.md
  FINAL_PROJECT_STATUS.md
```

Non aggiungere file se non servono davvero.

---

# 6. IL CUORE DA AGGIUNGERE: MONITORING CONFIG

Creare un solo file leggibile e modificabile:

```text
config/monitoring.yaml
```

Deve permettere di scegliere:

- cosa seguire;
- quali entità;
- quali temi;
- quali fonti;
- frequenza;
- priorità;
- finestra storica;
- se attivo o no.

Esempio:

```yaml
monitoring:

  - id: us_core
    enabled: true
    label: "Ujedinjena Srpska"
    entities:
      - US
      - STE
    topics:
      - elections_2026
      - coalition_relations
    source_groups:
      - rs_major_media
      - institutions
      - local_media
    runs_per_day: 12
    priority: high
    history_days: 7

  - id: doboj
    enabled: true
    label: "Doboj"
    entities:
      - DOBOJ
      - OBREN
      - JOSIC
    source_groups:
      - local_doboj
      - rs_major_media
    runs_per_day: 8
    priority: high
    history_days: 7

  - id: institutions
    enabled: true
    label: "Institutions"
    entities:
      - CIK
      - OHR
      - NSRS
    source_groups:
      - official
      - rs_major_media
      - bih_major_media
    runs_per_day: 6
    priority: medium
    history_days: 14

  - id: background
    enabled: true
    label: "General political environment"
    source_groups:
      - general_media
    runs_per_day: 3
    priority: low
    history_days: 30
```

---

# 7. FREQUENZA: NON TUTTO DEVE GIRARE UGUALE

Il sistema deve permettere frequenze diverse.

Raccomandazione iniziale:

| Priorità | Aggiornamenti |
|---|---:|
| HIGH | 8–12 volte/giorno |
| MEDIUM | 4–6 volte/giorno |
| LOW | 2–3 volte/giorno |
| ARCHIVE/BACKFILL | 1 volta/giorno |

Non è necessario interrogare tutte le fonti ogni 5 minuti.

Esempio:

```text
HIGH:
06:00
08:00
10:00
12:00
14:00
16:00
18:00
20:00
22:00
00:00

MEDIUM:
07:00
11:00
15:00
19:00
23:00

LOW:
08:00
16:00
23:00
```

La frequenza deve essere configurabile, non hardcoded.

---

# 8. DUE LIVELLI DI SCHEDULAZIONE

## LIVELLO 1 — SOURCES

Ogni fonte può avere:

```yaml
source_id: RS_ENT_001
enabled: true
schedule:
  runs_per_day: 8
```

## LIVELLO 2 — MONITORING TARGET

Ogni tema può avere una priorità propria:

```yaml
monitoring_id: doboj
runs_per_day: 12
```

Il collector deve scegliere le fonti rilevanti per quel monitoraggio.

Non duplicare inutilmente gli stessi fetch.

Se due target richiedono la stessa fonte nello stesso intervallo:

```text
1 fetch
→ più elaborazioni
```

---

# 9. SCHEDULER SEMPLICE

Per il primo rilascio:

```text
Windows Task Scheduler
```

oppure cron su server Linux.

Non costruire un orchestratore interno complesso.

La pipeline può essere lanciata con:

```bash
python -m pilot.run_all
```

Per il futuro può esistere:

```bash
python -m pilot.run_monitor --profile high
```

oppure:

```bash
python -m pilot.run_monitor --target doboj
```

Ma solo se porta un vantaggio reale.

---

# 10. HEALTH / STATO DELLO SCRAPER

La dashboard o un piccolo file tecnico deve dire:

```text
last_run
next_run
sources_enabled
sources_ok
sources_failed
new_items
new_events
new_trending
new_signals
duration
```

Esempio:

```json
{
  "last_run": "2026-08-28T22:00:00+02:00",
  "sources_enabled": 18,
  "sources_ok": 17,
  "sources_failed": 1,
  "new_items": 32,
  "new_events": 11,
  "duration_sec": 49
}
```

Se una fonte fallisce:

```text
non bloccare tutta la pipeline
```

ma registrare l'errore.

---

# 11. DASHBOARD: DEVE ESSERE SEMPLICE

La dashboard non deve mostrare tutta la complessità tecnica.

Homepage ideale:

```text
┌─────────────────────────────────────┐
│ ULTIMO AGGIORNAMENTO / STATO        │
├─────────────────────────────────────┤
│ SEMAFORI PRINCIPALI                 │
│ US | STE | US-SNSD | OPP | OHR ... │
├─────────────────────────────────────┤
│ TRENDING ADESSO                     │
│ 5-10 elementi                       │
├─────────────────────────────────────┤
│ SIGNAL DA GUARDARE                  │
│ solo quelli realmente rilevanti     │
├─────────────────────────────────────┤
│ ULTIME NOTIZIE IMPORTANTI           │
└─────────────────────────────────────┘
```

Non servono 50 KPI.

---

# 12. SEMAFORI

I semafori devono essere il centro operativo.

Ogni card deve mostrare solo:

```text
nome
stato
trend
ultima variazione
numero eventi recenti
numero fonti
```

Esempio:

```text
US
● VERDE
12 eventi / 24h
5 fonti
↑ +28% vs baseline
```

Click:

```text
→ dettaglio
→ eventi
→ articoli
→ fonti
→ timeline
```

---

# 13. TRENDING È PIÙ IMPORTANTE DEL VECCHIO SIGNAL_SCORE

Il ranking Beta 02 ha dimostrato che `signal_score` non ha abbastanza granularità.

Non usarlo come centro della dashboard.

Costruire Trending per entità.

Metriche minime:

```text
mentions_1h
mentions_4h
mentions_24h

unique_events_4h
unique_events_24h

unique_sources_4h
unique_sources_24h

acceleration

baseline_7d

share_of_voice_24h

last_event_at
```

---

# 14. ENTITY MOMENTUM

La domanda importante non è:

```text
chi ha più articoli?
```

ma:

```text
chi sta crescendo rispetto al suo normale?
```

Esempio:

```text
STE:
12 menzioni oggi
baseline = 3

→ momentum alto
```

contro:

```text
SNSD:
20 menzioni oggi
baseline = 18

→ volume alto
→ momentum basso
```

Questo è molto più utile per il Radar.

---

# 15. TRENDING.JSON

La pipeline deve generare:

```text
assets/data/trending.json
```

con dati reali.

Ogni voce dovrebbe contenere almeno:

```json
{
  "entity_id": "STE",
  "label": "Nenad Stevandić",
  "mentions_24h": 12,
  "unique_events_24h": 6,
  "unique_sources_24h": 5,
  "baseline_7d": 3.4,
  "momentum": 2.53,
  "last_event_at": "...",
  "top_events": [],
  "evidence": []
}
```

Se la baseline non è sufficiente:

```json
"baseline_7d": null
```

Non stimare.

---

# 16. SIGNAL ENGINE

Dopo Trending.

Signal = cambiamento significativo.

Input possibili:

```text
entity momentum
source diversity
event count
freshness
cross-reference
entity salience
verification
```

Output iniziale:

```text
MONITORING
REVIEW
```

Solo dopo test sufficienti:

```text
P2_CANDIDATE
P1_CANDIDATE
```

---

# 17. SIGNAL DEVE SPIEGARE “PERCHÉ”

Ogni Signal deve contenere:

```text
why_now
entities
events
metrics
sources
evidence
first_seen
last_seen
confidence
provenance
```

La dashboard deve permettere:

```text
Signal
→ Perché?
→ Eventi
→ Fonti
→ Articoli
```

---

# 18. ALERT E CASE RESTANO UMANI

Non creare automaticamente:

```text
P1 definitivo
Case
Task
Decision
```

Il sistema propone.

L'analista decide.

Flusso:

```text
Signal Candidate
        ↓
MEDIA / ANALISTA
        ↓
Alert
        ↓
eventuale Case
```

---

# 19. CASE / TASK / DECISION

Case:

```text
tema operativo
```

non:

```text
articolo
```

Task:

```text
azione concreta
```

Decision:

```text
decisione umana
```

Routing:

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

---

# 20. ARCHIVE

Archiviare:

```text
events
signals
alerts
cases
tasks
decisions
evidence
timeline
```

La domanda a cui deve rispondere:

> Cosa sapevamo in quel momento e perché è stata presa quella decisione?

---

# 21. DASHBOARD DATA CONTRACT

Prima di aggiungere API creare:

```text
docs/dashboard-data-contract.md
```

Per ogni file:

```text
rassegna.json
trending.json
signals.json
alerts.json
cases.json
tasks.json
archive.json
candidates.json
```

specificare:

```text
schema_version
required
optional
enum
date format
null policy
provenance
```

---

# 22. JSON STATICI PRIMA, API DOPO

Fase attuale:

```text
pipeline
→ JSON automatici
→ dashboard
```

È sufficiente.

Solo dopo stabilizzazione:

```text
GET /api/rassegna
GET /api/trending
GET /api/signals
...
```

Non costruire backend API prima che il contratto dati sia stabile.

---

# 23. FONTI

Il Source Registry resta centrale.

Ogni fonte deve avere almeno:

```text
source_id
name
url
method
source_type
enabled
priority
territory
owner_group
window_actual_days
last_success
last_error
```

`owner_group`:

```text
null
```

se non verificato.

Non dedurlo dal bias editoriale.

---

# 24. GDELT

Stato:

```text
VERIFICATO_NON_INTEGRATO
```

Usarlo eventualmente come:

```text
discovery
cross-check
source jump
external coverage
```

Non:

```text
GDELT → Signal diretto
GDELT → Case
```

---

# 25. YOUTUBE

Solo dopo la pipeline principale.

Usare API ufficiale.

Monitorare:

```text
partiti
leader
istituzioni
media
interviste
conferenze
```

Preferire:

```text
channel
→ uploads playlist
→ playlistItems
```

non global search continuo.

---

# 26. TERRITORIO / IJ

Oggi:

```text
territory_ij = null
```

Finché non esiste mapping verificato.

Serve task separato:

```text
fonte ufficiale
→ mapping comune/località
→ IJ
→ test
→ integrazione
```

Mai inventare IJ.

---

# 27. BACKFILL

Non deve più bloccare il progetto.

Serve per migliorare baseline.

Fare ancora:

- secondo giro sulle fonti troncate;
- audit RTRS.

Ma se una fonte non permette 30 giorni:

```text
documentare
→ continuare
```

Ogni giorno di produzione aumenta naturalmente lo storico reale.

---

# 28. BUG TECNICO ANCORA DA CHIUDERE

BL_IJ3_006 / Banjaluka24:

```text
trafilatura
→ include articoli correlati
```

Contaminazione misurata circa 71,4%.

Correggere con fix fonte-specifico.

Non cambiare il parser globale senza motivo.

---

# 29. CARD DASHBOARD ANCORA DA DECIDERE

9 card senza `modules` verificati:

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

Fare audit card-per-card.

Azioni:

```text
MAP
ADD_ENTITY
KEEP_NULL
REVIEW
```

Non inventare mapping.

---

# 30. COSA DEVE ESSERE PROGRAMMABILE DALL'UTENTE

Idealmente da config semplice:

```text
ON/OFF
fonti
tema
entità
priorità
runs_per_day
history_days
```

Esempio:

```yaml
id: doboj
enabled: true
entities:
  - DOBOJ
  - OBREN
sources:
  - RTV_DOBOJ
  - INFOBIJELJINA
runs_per_day: 8
history_days: 7
```

Questo è il requisito centrale del prodotto.

---

# 31. EVENTUALE PANNELLO “IMPOSTAZIONI SCRAPER”

In futuro la dashboard può avere una pagina semplice:

```text
MONITORAGGIO
```

con:

| Monitor | Stato | Frequenza |
|---|---|---|
| US | ON | 12/giorno |
| Stevandić | ON | 12/giorno |
| Doboj | ON | 8/giorno |
| OHR | ON | 6/giorno |
| CIK | ON | 6/giorno |
| Generale RS | ON | 3/giorno |

Bottoni:

```text
Attiva
Disattiva
Modifica frequenza
Esegui ora
```

Non serve per MVP se il file YAML è più semplice.

---

# 32. COSA DEVE MOSTRARE LA DASHBOARD OGNI GIORNO

## HOME

1. ultimo aggiornamento;
2. stato scraper;
3. semafori;
4. Trending;
5. Signal;
6. ultime notizie rilevanti.

## CARD DETTAGLIO

1. stato;
2. andamento;
3. eventi;
4. fonti;
5. articoli;
6. timeline.

## RASSEGNA

filtri:

```text
fonte
tempo
entità
tema
territorio
lingua
```

## ARCHIVE

ricerca storica.

---

# 33. COSA NON MOSTRARE IN HOME

Non mettere in primo piano:

- raw counts tecnici;
- hash;
- cosine score;
- cluster internals;
- boilerplate;
- confidence tecnica di ogni parser;
- centinaia di KPI.

Questi appartengono al debug.

---

# 34. LOGICA DI PRIORITÀ DASHBOARD

Priorità visuale:

```text
1. US
2. Nenad Stevandić
3. US candidates / organization
4. US relations
5. competitors / opposition
6. NSRS / OHR / CIK / Elections 2026 / Belgrade
7. territory / local
```

Ma le priorità devono stare in config, non hardcoded ovunque.

---

# 35. TEST MINIMI PRIMA DELLA CHIUSURA

## Scraper

- tutte le fonti abilitate testate;
- errore di una fonte non blocca tutto;
- duplicati non ricompaiono;
- date valide;
- Unicode/cirillico intatto.

## Trending

- baseline controllata;
- volume ≠ momentum;
- stessa entità aggregata correttamente;
- evidence presente.

## Dashboard

- `rassegna.json` reale;
- `trending.json` reale;
- `signals.json` reale;
- nessun errore JS;
- responsive;
- semafori cliccabili;
- dettaglio con evidence.

## Workflow

- nessun P1 automatico;
- nessun Case senza evidence;
- GO non invia a VRH;
- audit minimo presente.

---

# 36. DEFINITION OF DONE FINALE

Il progetto è concluso quando:

- [ ] lo scraper gira automaticamente;
- [ ] frequenza configurabile;
- [ ] fonti configurabili;
- [ ] temi/entità configurabili;
- [ ] errori fonti registrati;
- [ ] pipeline ripetibile con un comando;
- [ ] `rassegna.json` reale;
- [ ] `trending.json` reale;
- [ ] `signals.json` reale;
- [ ] dashboard semplice;
- [ ] semafori funzionanti;
- [ ] Trending utile;
- [ ] Signal spiegabili;
- [ ] evidence accessibile;
- [ ] Alert/Case restano sotto controllo umano;
- [ ] Archive ricostruibile;
- [ ] tutti i test verdi;
- [ ] documentazione aggiornata;
- [ ] nessun dato inventato;
- [ ] nessun componente inutile.

---

# 37. ORDINE FINALE DEI LAVORI

```text
1. FIX Banjaluka24
2. secondo backfill
3. monitoring.yaml
4. scheduler configurabile
5. trending engine per entità
6. trending.json reale
7. audit 9 card mancanti
8. entity salience / momentum
9. signal candidates
10. signals.json reale
11. semafori collegati ai dati reali
12. detail/evidence
13. workflow Alert/Case
14. Archive
15. health/status scraper
16. documentazione finale
17. solo dopo: eventuale API backend
```

---

# 38. REGOLE NON NEGOZIABILI

```text
NO overengineering
NO hallucination
NO invented sources
NO invented RSS
NO invented IJ
NO inferred ownership
NO LLM → P1 automatico
NO article → Case automatico
NO frontend rewrite
NO thresholds changed just to pass KPI
```

Dato non verificato:

```text
null
```

---

# 39. PROMPT FINALE PER CLAUDE CODE / CODEX / CURSOR

```text
Sei incaricato di CONCLUDERE il progetto MEDIA PILOT / RADAR POLITICO.

Prima di scrivere codice leggi:

- docs/BETA_RESULTS.md
- docs/TASK_BETA_02_RESULTS.md
- docs/HANDOFF_PROGRESS.md
- docs/RFC_SECONDA_OPINIONE_02.md
- docs/MEDIA_SCRAPER_BUILD_GUIDE.md
- docs/MEDIA_PILOT_FINAL_HANDOFF.md
- dashboard-config.js
- data.js
- assets/data/*.json
- config/*.yaml
- pilot/*.py

OBIETTIVO FINALE:

Avere un sistema semplice che:

1. raccoglie informazioni vere;
2. può essere programmato su COSA monitorare;
3. può essere programmato su QUANTE VOLTE AL GIORNO aggiornare;
4. produce automaticamente i JSON usati dalla dashboard;
5. mostra una dashboard semplice con:
   - semafori;
   - Trending;
   - Signal;
   - rassegna;
   - evidence;
6. lascia Alert, Case e decisioni sotto controllo umano.

NON rifare ciò che è già chiuso nella Beta 02.

ORDINE:

A. correggi BL_IJ3_006/Banjaluka24;
B. completa il secondo giro di backfill già possibile;
C. crea config/monitoring.yaml;
D. implementa scheduler/configurazione frequenze senza overengineering;
E. crea Trending Engine per entità:
   mentions_1h/4h/24h,
   unique_events,
   unique_sources,
   acceleration,
   baseline_7d,
   share_of_voice,
   momentum,
   evidence;
F. genera assets/data/trending.json reale;
G. fai audit delle 9 card senza modules;
H. costruisci SignalCandidate deterministici e spiegabili;
I. genera assets/data/signals.json reale;
J. collega semafori e detail view ai dati reali;
K. aggiungi scraper health/status;
L. completa Archive/workflow umano solo dopo che Rassegna/Trending/Signal funzionano.

VINCOLI:

- no nuove dipendenze salvo necessità dimostrata;
- no vector DB;
- no Elasticsearch;
- no Kafka;
- no microservizi;
- no riscrittura dashboard;
- no LLM obbligatorio;
- no P1 automatico;
- no Case automatico;
- dato non verificato = null;
- ogni Signal deve avere evidence;
- ogni modifica deve avere test.

Per ogni fase:

PLAN
→ IMPLEMENT
→ TEST
→ REPORT
→ CHECK

Aggiorna:

docs/HANDOFF_PROGRESS.md

e crea alla fine:

docs/FINAL_PROJECT_STATUS.md

con:

- cosa funziona;
- cosa resta manuale;
- configurazione scheduler;
- fonti attive;
- frequenze;
- JSON reali prodotti;
- test;
- limiti noti;
- istruzioni operative.

FERMATI solo quando il sistema completo può essere eseguito e aggiornare la dashboard in modo ripetibile.
```

---

# 40. RISULTATO FINALE DESIDERATO

Una persona deve poter fare:

```text
1. aprire monitoring.yaml
2. scegliere cosa monitorare
3. scegliere frequenza
4. salvare
```

e poi il sistema deve:

```text
raccogliere
→ pulire
→ deduplicare
→ raggruppare eventi
→ calcolare trending
→ produrre signal
→ aggiornare dashboard
```

senza interventi tecnici quotidiani.

La dashboard deve rispondere rapidamente a tre domande:

```text
1. Cosa sta succedendo?
2. Cosa sta cambiando?
3. Perché dovrei guardarlo?
```

Se riesce a fare questo in modo affidabile, il progetto è concluso.
