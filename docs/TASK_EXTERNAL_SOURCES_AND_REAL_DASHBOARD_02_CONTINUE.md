# TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_CONTINUE
## MEDIA PILOT — Continuazione dopo interruzione / rate limit

**Stato:** CONTINUE_FROM_CURRENT_REPO_STATE  
**Priorità:** IMMEDIATA  
**Regola:** NON ripartire da zero. NON rifare audit già presenti. NON usare overengineering.  
**Modalità consigliata:** lavorare nella sessione principale, sequenzialmente. Evitare nuovi background agent/fork salvo necessità reale.

---

# 0. SCOPO

Continuare e CHIUDERE:

```text
TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md
```

partendo dallo stato REALE del repository dopo l'interruzione della sessione precedente.

Il task precedente era diviso in:

```text
BLOCCO A
external source pilot / pipeline

BLOCCO B
dashboard demo cleanup

CONSOLIDAMENTO
report + status docs
```

La sessione è stata interrotta prima della chiusura.

NON ricominciare il task completo.

---

# 1. STATO GIÀ NOTO

La Beta Dashboard precedente è già completata.

Non rifarla.

Risultati già verificati:

```text
semafori reali grey/green/amber
0 red automatici
HOME con pipeline status
Trending reale
Signal REVIEW reali
Rassegna reale
sidebar desktop collapsible
mobile drawer
data.js per-file isolation
_selftest_beta.html = 13/13 PASS
```

---

# 2. STATO DEL TASK 02 DOPO L'INTERRUZIONE

Sono già presenti:

```text
docs/EXTERNAL_SCRAPER_AUDIT_V2.md
docs/SOURCE_GAPS_AUDIT.md
```

Questi sono output del precedente BLOCCO A.

NON rigenerarli automaticamente.

Prima leggerli e verificare se sono completi/coerenti con il codice.

Al momento del resume risultavano invece ASSENTI:

```text
docs/DASHBOARD_REAL_DATA_AUDIT.md
docs/TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md
```

Quindi il BLOCCO B e il consolidamento finale NON risultavano chiusi.

---

# 3. PRIMA AZIONE: AUDIT DELLO STATO REALE

Prima di scrivere codice:

```text
git status
git diff
```

Poi controllare se esistono modifiche parziali lasciate dal Fork A.

Verificare almeno:

```text
pilot/external/
config/sources.yaml
pilot/test_pipeline.py
pilot/score.py
pilot/run_all.py
pilot/collect.py
docs/EXTERNAL_SCRAPER_AUDIT_V2.md
docs/SOURCE_GAPS_AUDIT.md
```

Classificare ogni elemento:

```text
DONE
PARTIAL
NOT_DONE
```

### Regola

Se Fork A ha già scritto codice valido:
- NON riscriverlo;
- testarlo;
- completare solo ciò che manca.

Se Fork A ha prodotto solo documentazione:
- scegliere il provider in base agli audit;
- implementare SOLO il minimo necessario.

---

# 4. BLOCCO A — CHIUDERE SOLO SE INCOMPLETO

Il BLOCCO A deve terminare con:

```text
1 solo provider selezionato
oppure
NONE QUALIFY / REJECT
```

Non è obbligatorio integrare qualcosa.

## Verificare

### A. Provider scelto

Documentare:

```text
provider
ruolo
perché
problema reale che risolve
```

Possibili ruoli:

```text
KEEP
DISCOVERY_ONLY
FALLBACK_ONLY
REJECT
```

### B. Adapter

Se esiste:

```text
pilot/external/<provider>_adapter.py
```

deve essere MINIMO.

Non creare framework plugin.

### C. Provenance

Ogni articolo esterno deve preservare:

```text
original_url
original_domain
published_at
provider
```

### D. source_diversity

Il provider NON deve essere contato come fonte editoriale.

Esempio:

```text
open-news -> rtrs.tv
```

deve contare:

```text
rtrs.tv = 1
```

NON:

```text
open-news + rtrs.tv = 2
```

### E. Error isolation

Provider fallisce:

```text
pipeline continua
```

Provider disabled:

```text
zero fetch
zero overhead significativo
```

### F. Baseline vs Pilot

Se possibile misurare realmente:

```text
BASELINE
external_items_total = 0
raw
clean
relevant
domains
events

PILOT
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

Non dichiarare valore incrementale senza misurazione.

---

# 5. NON FORZARE UN PROVIDER

Se l'audit mostra:

```text
molti duplicati
nessun nuovo dominio utile
nessun nuovo evento
nessuna migliore tempestività
troppo runtime
dipendenze sproporzionate
```

decisione valida:

```text
REJECT
```

oppure:

```text
DISCOVERY_ONLY
```

NON integrare un provider solo perché il task lo aveva previsto.

---

# 6. BLOCCO B — FINIRE ORA

Questo blocco era quello rimasto incompleto.

Lavorare direttamente sui file frontend REALI.

Auditare:

```text
index.html
styles.css
app.js
radar.js
ui.js
data.js
dashboard-config.js
page-vrh.js
page-media.js
page-eksperti.js
page-case.js
page-simulator.js
page-arhiva.js
```

solo se realmente presenti.

Cercare:

```text
demo
mock
fake
sample
placeholder
fallback
seed
hardcoded
Math.random
static alert
static case
static task
static decision
```

Creare:

```text
docs/DASHBOARD_REAL_DATA_AUDIT.md
```

Tabella minima:

| Modulo/file | Dataset | REAL/DEMO/MIXED/UNUSED | Azione |
|---|---|---|---|

---

# 7. HOME OPERATIVA = SOLO REAL

La HOME normale deve usare esclusivamente:

```text
assets/data/rassegna.json
assets/data/trending.json
assets/data/signals.json
data/pipeline_health.json
```

e altri dataset solo se realmente generati dalla pipeline e documentati.

### NON deve usare

```text
alerts demo
cases demo
tasks demo
decisions demo
archive demo
candidate demo
```

per:

```text
KPI
semafori
status
trending
signal
home cards
conteggi
```

---

# 8. MODULI DEMO

Non cancellare necessariamente il codice storico utile.

Separarlo chiaramente.

Preferenza:

```text
navigazione operativa
    ↓
solo moduli reali
```

e:

```text
demo/dev
    ↓
VRH
Case
Alert
Task
Simulator
Archive demo
```

Soluzioni semplici accettate:

```text
badge DEMO visibile
menu secondario DEV/DEMO
?demo=1
```

Scegliere la soluzione MINIMA coerente con il frontend esistente.

La navigazione operativa standard NON deve far credere che i moduli demo siano reali.

---

# 9. FIX PIPELINE STATUS

Verificare il bug già individuato:

```text
sources_failed
```

può essere array/lista, non numero.

La UI deve gestire correttamente il tipo REALE scritto da:

```text
data/pipeline_health.json
```

Non cambiare il backend solo per adattarlo a una supposizione frontend se il formato attuale è documentato.

---

# 10. HEALTH STATES

La UI operativa deve distinguere realmente:

```text
ONLINE
DEGRADED
DATA UNAVAILABLE
```

### ONLINE

health disponibile e nessun errore significativo.

### DEGRADED

health disponibile ma fonti fallite / errori rilevanti.

### DATA UNAVAILABLE

`pipeline_health.json` mancante/non leggibile.

NON mostrare ONLINE come fallback.

---

# 11. SEMAFORI

Conservare la Beta:

```text
GRIGIO
nessun dato / insufficiente

VERDE
monitoraggio normale

AMBRA
Signal REVIEW reale

ROSSO
solo futuro Alert umano reale
```

Divieti:

```text
no red automatico
no random
no demo status
no fake priority
```

---

# 12. RESPONSIVE — CHIUDERE IL GAP

Verificare realmente:

```text
390 px
768 px
1280 px
1920 px
```

Per ciascuno:

```text
sidebar/drawer
semafori
Trending
Signal
Rassegna
sheet/detail
overflow
leggibilità
```

Non è obbligatorio produrre screenshot se il tool non funziona.

Sono accettabili misure DOM/iframe reali documentate.

Ma NON scrivere "verified" senza una verifica concreta.

---

# 13. TEST

Prima:

```text
python -m pilot.test_pipeline
```

Poi frontend:

```text
_selftest_beta.html
```

Atteso minimo:

```text
13/13 PASS
```

Aggiungere SOLO test necessari per le nuove modifiche.

Verificare:

```text
provider disabled = zero fetch
provider failure isolated
original URL preserved
source_diversity corretta
no demo fallback
HOME solo real data
no automatic red
missing JSON does not crash
sources_failed rendered correctly
responsive no blocking overflow
```

---

# 14. NON TOCCARE SENZA REGRESSIONE DIMOSTRATA

NON riaprire:

```text
dedup
TF-IDF
cosine thresholds
clustering thresholds
backfill
Banjaluka24 clean fix
signal weights
Trending algorithm
Signal thresholds
monitoring.yaml
run_monitor.py
```

Questi sono già lavori chiusi.

---

# 15. NON FARE ORA

Non costruire:

```text
Alert workflow reale
Case workflow
Task workflow
Decision workflow
Archive operativo
nuovo backend
nuovo database
API server
React/Vue
secondo provider esterno
custom RSS bridges per ogni sito
```

---

# 16. DOCUMENTO RISULTATI FINALE

Quando BLOCCO A + BLOCCO B sono realmente chiusi creare:

```text
docs/TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md
```

Struttura obbligatoria:

## 1. Stato iniziale

```text
cosa esisteva già
cosa era incompleto
```

## 2. External source audit

```text
repository valutati
provider scelto
oppure none qualify
```

## 3. Source gaps

```text
problemi reali identificati
```

## 4. Adapter

```text
file
ruolo
schema
provenance
```

## 5. Baseline vs Pilot

Tabella:

| Metrica | Baseline | Pilot | Delta |
|---|---:|---:|---:|

Includere almeno:

```text
raw/items
relevant
domains
events
duplicates
new relevant
errors
runtime
```

## 6. Decisione provider

Una sola:

```text
KEEP
DISCOVERY_ONLY
FALLBACK_ONLY
REJECT
```

## 7. Dashboard real-data audit

```text
dataset REAL
dataset DEMO
dataset MIXED
azioni effettuate
```

## 8. Demo separation

```text
cosa è visibile nel menu operativo
cosa resta DEV/DEMO
```

## 9. Health

```text
ONLINE
DEGRADED
DATA UNAVAILABLE
```

## 10. Responsive

```text
390
768
1280
1920
```

## 11. Tests

```text
backend X/X
frontend 13/13
console
```

## 12. Limiti residui

Solo problemi REALI rimasti.

---

# 17. AGGIORNARE STATUS DOC

Solo DOPO il report finale:

```text
docs/FINAL_PROJECT_STATUS.md
docs/HANDOFF_PROGRESS.md
```

Devono riflettere il codice realmente presente.

Non copiare vecchi stati non più veri.

---

# 18. DEFINITION OF DONE

Il task è chiuso quando:

- [ ] stato Fork A verificato;
- [ ] audit esistenti riusati, non rifatti inutilmente;
- [ ] 1 provider selezionato oppure NONE QUALIFY;
- [ ] eventuale adapter minimo testato;
- [ ] provenance corretta;
- [ ] source_diversity corretta;
- [ ] baseline/pilot misurati se provider integrato;
- [ ] `DASHBOARD_REAL_DATA_AUDIT.md` creato;
- [ ] HOME senza dati simulati;
- [ ] demo separate chiaramente;
- [ ] `sources_failed` gestito correttamente;
- [ ] ONLINE/DEGRADED/DATA UNAVAILABLE reali;
- [ ] responsive 390/768/1280/1920 verificato;
- [ ] backend tests verdi;
- [ ] `_selftest_beta.html` verde;
- [ ] `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02_RESULTS.md` creato;
- [ ] `FINAL_PROJECT_STATUS.md` aggiornato;
- [ ] `HANDOFF_PROGRESS.md` aggiornato.

---

# 19. STOP CONDITION

Quando tutto sopra è chiuso:

```text
STOP
```

NON iniziare automaticamente il prossimo task.

Il prossimo passo verrà deciso dopo lettura dei risultati.

---

# 20. MODALITÀ DI LAVORO

Usare:

```text
READ CURRENT STATE
→ VERIFY PARTIAL WORK
→ FINISH BLOCCO A ONLY IF NEEDED
→ FINISH BLOCCO B
→ TEST
→ CONSOLIDATE
→ REPORT
→ STOP
```

### Regole finali

```text
NO OVERENGINEERING
NO OVERTHINKING
NO REWRITE
NO HALLUCINATION
NO REDESIGN OF WORKING PIPELINE
NO SECOND PROVIDER
```

Se qualcosa non è dimostrabile:

```text
UNKNOWN
NULL
REVIEW
```

Non indovinare.

Finire autonomamente senza chiedere conferme per micro-decisioni tecniche.
