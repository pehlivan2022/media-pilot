# TASK_SOURCE_EXPANSION_DAILY_PILOT_01
## MEDIA PILOT — Test nuove fonti, promozione controllata e profilo scraping 1×/giorno

**Stato:** READY_FOR_IMPLEMENTATION  
**Priorità:** PRIMA DEL WINDOWS TASK SCHEDULER DEFINITIVO  
**Scope:** SOURCE REGISTRY + SOURCE TESTING + DAILY PILOT ONLY  
**Principio:** testare prima, aggiungere dopo, registrare ogni problema.  
**Vincoli:** NO overengineering, NO browser automation salvo necessità già dimostrata, NO social scraping automatico, NO riscrittura pipeline.

---

# 0. OBIETTIVO

Prima di registrare lo scheduler definitivo:

1. confrontare le nuove liste fonti con `config/sources.yaml`;
2. identificare le fonti realmente mancanti;
3. testare tecnicamente i siti;
4. aggiungere SOLO le fonti che superano i test;
5. registrare chiaramente le fonti problematiche e il motivo;
6. creare un profilo temporaneo per eseguire **tutte le fonti abilitate 1 volta al giorno**;
7. fare almeno un run reale immediato;
8. STOP.

Il task NON deve aumentare la frequenza oltre 1×/giorno.

---

# 1. INPUT — GERARCHIA DEI FILE

Usare come base principale:

```text
media_pilot_fonti_facebook_aggiornate_v14.xlsx
```

Foglio principale:

```text
01_MASTER_ALL
```

Questa è la lista candidata canonica per questo task.

Dati osservati nella v14:

```text
110 fonti totali
108 con website_url
2 senza website_url
100 con status_tag = VERIFICATA
9 con status_tag = MANCANTE
1 con status_tag = DA_VERIFICARE
```

Rispetto alla v12 compatibile, la v14 aggiunge una sola anagrafica:

```text
PART_RS_ZPIR_001
Za pravdu i red
https://zapravduired.org/
```

Gli altri file sono SOLO cross-check/provenance:

```text
media_pilot_master_sources_v12_COMPATIBILISSIMO.csv
media_pilot_facebook_fonti_taggate_v13.xlsx
media_pilot_facebook_fonti_taggate_v13.csv
media_pilot_fonti_unico_v11_SOCIAL_AGGIORNATO.xlsx
facebook_urls_verificati_2.xlsx
aebcdd74-f407-4026-be79-9dcc7f59d46a.xlsx
social_ok_.xlsx
media_pilot_izvori Cvije_sve zivo i mrtvo.xlsx
```

NON fondere ciecamente tutti i file.

Precedenza:

```text
v14
↓
v12/v13 per verifica storica
↓
file social verificati
↓
v11 / Cvije solo come riferimento storico
```

Se i file non sono già nella repo, copiarli in:

```text
input/source_candidates/
```

NON versionare file temporanei se la repo non li richiede.

---

# 2. STATO CORRENTE DEL PROGETTO

`config/sources.yaml` contiene già fonti operative e verificate.

Il progetto aveva già raggiunto **18 fonti attive** prima di questo task.

NON riaggiungere fonti già presenti.

NON assumere che il `source_id` dei fogli Excel coincida sempre con il `source_id` corrente.

### Matching obbligatorio

Confrontare in questo ordine:

```text
1. canonical website domain
2. website_url normalizzato
3. nome fonte
4. source_id
```

Il dominio è più importante del solo ID.

Se:

```text
stesso dominio
ma source_id diverso
```

classificare:

```text
ID_CONFLICT / ALREADY_ACTIVE
```

e NON creare una seconda fonte.

---

# 3. NON TOCCARE LA PIPELINE

NON modificare, salvo bug dimostrato:

```text
pilot/clean.py
pilot/dedup.py
pilot/score.py
pilot/trending.py
pilot/signals.py
pilot/run_all.py
pilot/run_monitor.py
```

NON cambiare:

```text
TF-IDF
cosine thresholds
dedup thresholds
signal weights
Signal rules
```

Questo task riguarda le FONTI.

---

# 4. PRIMO OUTPUT — INVENTARIO DIFFERENZIALE

Creare:

```text
docs/SOURCE_EXPANSION_AUDIT_01.csv
```

e:

```text
docs/SOURCE_EXPANSION_AUDIT_01.md
```

Per ogni riga della v14:

```text
source_id_candidate
name
website_url
canonical_domain
macro_tipo
priority_tier
technical_access
already_active
current_source_id
test_status
fetch_method_found
feed_url
http_status
items_recent
valid_articles
fulltext_ok
date_ok
duplicate_rate_sample
problem
decision
notes
```

---

# 5. STATUS CONSENTITI

Usare status chiari e limitati:

```text
ALREADY_ACTIVE
READY_RSS
READY_HTML
READY_SITEMAP
READY_OFFICIAL_LOW_VOLUME
BLOCKED_403
BLOCKED_429
ROBOTS_RESTRICTED
JS_ONLY
NO_RSS
NO_ARTICLE_LINKS
NO_DATE
EMPTY_CONTENT
BAD_EXTRACTION
DUPLICATE_DOMAIN
ID_CONFLICT
REDIRECTED
DEAD_DOMAIN
TIMEOUT
SSL_ERROR
SOCIAL_ONLY
NOT_USEFUL
MANUAL_REVIEW
```

Non inventare categorie ad ogni problema.

---

# 6. ORDINE DI TEST

## PASS A — PRIORITY TIER 1

Testare prima tutte le fonti v14 con:

```text
priority_tier = 1
```

Nella v14 sono 24 siti web.

Lista di riferimento:

```text
BIH_ELEC_001  Centralna izborna komisija BiH
BIH_ELEC_002  Koalicija Pod lupom
BIH_ELEC_003  Transparency International BiH
RS_IJ_001     BN / RTV BN
BL_IJ3_001    Srpskainfo
RS_ENT_001    RTRS
RS_ENT_002    ATV
BL_IJ3_002    Nezavisne novine
BL_IJ3_003    Glas Srpske
POL_RS_001    SNSD
BL_IJ3_006    Banjaluka24
POL_RS_003    PDP
BL_IJ3_011    Grad Banja Luka
BL_IJ3_007    BL Portal
POL_RS_004    Ujedinjena Srpska
RS_IJ_013     Dobojski.info
RS_IJ_017     Grad Doboj
POL_RS_002    SDS
RS_IJ_012     Glas Regije
RS_IJ_014     RTV Doboj
RS_IJ_018     InfoBijeljina
ECO_001       Capital.ba
FBIH_001      Klix.ba
SRC_009       N1 BiH
```

Molte sono già attive.

Il primo compito è quindi il DIFF, non il fetch.

---

# 7. PASS B — TIER 2 MIRATO

Dopo Tier 1, testare Tier 2 NON attive con priorità a:

```text
Doboj / IJ5
Ujedinjena Srpska
partiti RS
istituzioni elettorali
media RS locali
economia / investigativo
BiH monitoring
```

NON testare automaticamente tutte le 110 fonti con scraping aggressivo.

Per Tier 2 fare prima un HTTP/RSS discovery leggero.

---

# 8. PASS C — TIER 3 SOLO SE UTILE

Tier 3:

```text
audit leggero
```

Promuovere solo se colma un gap geografico o tematico reale.

NON aggiungere fonti solo per aumentare il numero totale.

---

# 9. STRATEGIA DI FETCH PER OGNI SITO

Per ogni candidato NON attivo:

## 1. HTTP base

Testare:

```text
homepage
robots.txt
```

## 2. RSS discovery

Cercare in modo leggero:

```text
<link rel="alternate" ...>
/feed/
/rss
/rss.xml
/feed.xml
```

e percorsi già noti dal sito.

## 3. Sitemap

Solo se RSS assente o insufficiente:

```text
/sitemap.xml
robots.txt Sitemap:
```

## 4. HTML

Solo se RSS/sitemap non risolvono:

```text
homepage article links
article page
```

### Preferenza

```text
RSS
>
sitemap + HTTP
>
HTML
```

---

# 10. NO BROWSER AUTOMATION

NON introdurre:

```text
Playwright
Selenium
Chromium
browser headless
```

solo perché una fonte è difficile.

Se una fonte richiede JS:

```text
JS_ONLY
```

e proseguire.

Non blocca il task.

---

# 11. FACEBOOK / INSTAGRAM / X

I file contengono molti URL social verificati.

In questo task:

```text
NON SCRAPARE FACEBOOK
NON SCRAPARE INSTAGRAM
NON SCRAPARE X
```

Usarli SOLO come:

```text
metadata
provenance
link di verifica
future discovery reference
```

La v14 ha già un ampio lavoro di verifica Facebook.

Non duplicare quel lavoro.

Social scraping sarà un task separato solo se verrà scelto un metodo stabile.

---

# 12. TEST ARTICOLI

Per una fonte candidata raccogliere un piccolo sample.

Target:

```text
max 10 articoli recenti
```

Verificare almeno:

```text
URL originale
title
published_at
text
source/domain
```

### READY

Fonte pronta se:

```text
>= 3 articoli validi recenti
```

oppure se è una fonte istituzionale/partitica a basso volume ma strategicamente utile:

```text
READY_OFFICIAL_LOW_VOLUME
```

---

# 13. QUALITÀ MINIMA

Per sample:

```text
title non vuoto
original_url valida
published_at leggibile quando presente
text non vuoto / non menu
nessun blocco related articles dominante
nessun duplicato strutturale evidente
```

Se il fulltext è contaminato:

```text
BAD_EXTRACTION
```

NON aggiungere un fix source-specific in questo task salvo soluzione banale e locale già supportata dal collector.

---

# 14. CRITERIO DI PROMOZIONE

Aggiungere in `config/sources.yaml` SOLO se:

```text
READY_RSS
READY_HTML
READY_SITEMAP
READY_OFFICIAL_LOW_VOLUME
```

e:

```text
non già attiva
non duplicate-domain
nessun ID conflict irrisolto
```

---

# 15. LIMITE DI NUOVE FONTI

Per evitare di destabilizzare il Beta:

```text
MAX 15 nuove fonti abilitate in questo task
```

Se più di 15 sono READY:

ordinare per:

```text
1. priority_tier
2. Doboj/IJ5 relevance
3. US/RS election relevance
4. institutional importance
5. incremental domain coverage
6. technical reliability
```

Le restanti READY:

```text
READY_NOT_ENABLED_YET
```

nel report.

Non serve aggiungere tutto subito.

---

# 16. SOURCE ID

Per una nuova fonte:

- usare il `source_id` v14 SOLO se non collide;
- se collide con un'altra fonte corrente, NON rinominare automaticamente;
- mettere:

```text
MANUAL_REVIEW / ID_CONFLICT
```

La correttezza della provenance vale più della velocità.

---

# 17. OWNER_GROUP / BIAS / METADATI POLITICI

NON inferire nuovi:

```text
owner_group
political_alignment
political_code
```

dai nomi dei media.

Se non verificati:

```text
null
```

Preservare invece i campi descrittivi della v14 solo come metadata di registry se compatibili.

---

# 18. BACKFILL

Per le nuove fonti:

NON fare backfill massiccio.

Prima integrazione:

```text
recent only
```

preferenza:

```text
1–7 giorni
```

in base al metodo disponibile.

L’obiettivo ora è stabilità giornaliera, non costruire storico.

---

# 19. DEDUP TEST

Dopo aver aggiunto le nuove fonti:

fare un run con:

```text
python -m pilot.run_all
```

o l’entry point corrente equivalente.

Misurare:

```text
raw new
clean new
deduped new
relevant new
clusters new
```

Per ogni nuova fonte:

```text
fetched
valid
duplicates
survived_dedup
relevant
```

---

# 20. COPERTURA INCREMENTALE

Una fonte può essere tecnicamente READY ma poco utile.

Segnalare:

```text
incremental_value = HIGH / MEDIUM / LOW
```

basandosi su:

```text
nuovi domini
nuovi articoli rilevanti
nuovi eventi
copertura locale
copertura istituzionale
```

NON basarlo sul volume puro.

---

# 21. PROBLEMI DA REGISTRARE

Creare:

```text
docs/SOURCE_PROBLEMS_01.csv
```

Campi:

```text
source_id
name
url
timestamp
problem_code
http_status
stage
detail
retryable
recommended_action
```

Esempi:

```text
BLOCKED_403
RSS_EMPTY
TIMEOUT
BAD_EXTRACTION
NO_DATE
DUPLICATE_DOMAIN
JS_ONLY
```

Ogni problema deve restare auditabile.

---

# 22. NON CANCELLARE FONTI ESISTENTI

Se una fonte attiva fallisce durante questo audit:

NON eliminarla automaticamente.

Registrare:

```text
REGRESSION_EXISTING_SOURCE
```

e lasciare l’attuale config invariata salvo errore evidente.

---

# 23. PROFILO TEMPORANEO 1×/GIORNO

Dopo la promozione delle nuove fonti, creare in:

```text
config/monitoring.yaml
```

un target temporaneo, SOLO se lo schema corrente lo consente senza modifica a `run_monitor.py`.

Nome suggerito:

```text
pilot_daily_all
```

Deve contenere:

```text
tutte le source_id enabled
runs_per_day: 1
```

NON cancellare o sostituire gli attuali target:

```text
us_core
doboj
institutions
opposition_competitors
background
```

Questo è un profilo PILOT temporaneo.

---

# 24. SE IL TARGET "ALL" NON È SUPPORTATO

NON modificare `run_monitor.py`.

In tal caso creare solo documentazione:

```text
docs/DAILY_ALL_SOURCES_COMMAND.md
```

con il comando semplice già supportato dal progetto per eseguire tutte le fonti una volta.

Niente nuovo orchestratore.

---

# 25. RUN REALE IMMEDIATO

Eseguire una volta:

```text
pilot_daily_all
```

oppure l’equivalente supportato.

Registrare:

```text
start
end
duration
sources attempted
sources OK
sources failed
new items
relevant
signals REVIEW
```

---

# 26. 1×/GIORNO — NON ANCORA SCHEDULER DEFINITIVO

Questo task NON deve ancora registrare Windows Task Scheduler.

Deve solo lasciare pronto:

```text
target/comando 1×/day
```

Il task successivo:

```text
TASK_WINDOWS_SCHEDULER_01
```

registrerà la schedulazione.

Per il primo periodo operativo useremo:

```text
1 run / giorno
```

prima di aumentare la frequenza.

---

# 27. CRITERIO PER AUMENTARE FREQUENZA IN FUTURO

NON implementare ora.

Dopo alcuni giorni:

```text
fonti stabili
runtime accettabile
pochi errori
segnali utili
```

potremo dividere:

```text
high
medium
low
```

con frequenze diverse.

Ora:

```text
1×/day
```

è intenzionalmente conservativo.

---

# 28. TEST

Tutti i test esistenti devono restare verdi.

Eseguire:

```text
python -m pilot.test_pipeline
```

Atteso almeno lo stato corrente.

Aggiungere test SOLO se serve per:

```text
source canonical matching
duplicate-domain protection
new source parser
```

Non creare un framework di test nuovo.

---

# 29. OUTPUT FINALI

Creare:

```text
docs/SOURCE_EXPANSION_AUDIT_01.csv
docs/SOURCE_EXPANSION_AUDIT_01.md
docs/SOURCE_PROBLEMS_01.csv
docs/TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md
```

Aggiornare:

```text
docs/FINAL_PROJECT_STATUS.md
docs/HANDOFF_PROGRESS.md
```

---

# 30. REPORT RISULTATI

`TASK_SOURCE_EXPANSION_DAILY_PILOT_01_RESULTS.md` deve riportare:

## Input

```text
v14 rows
website URLs
tier distribution
```

## Current

```text
sources active before
```

## Diff

```text
already active
new candidates
duplicates
ID conflicts
missing website
```

## Tests

```text
READY_RSS
READY_HTML
READY_SITEMAP
READY_OFFICIAL_LOW_VOLUME
blocked
dead
JS-only
manual review
```

## Added

Tabella:

| source_id | name | domain | method | recent items | decision |
|---|---|---|---|---:|---|

## Problems

Tabella sintetica per problem_code.

## Before / After

```text
active sources
raw
clean
dedup
relevant
clusters
signals review
runtime
```

## Daily mode

```text
pilot_daily_all created = yes/no
runs_per_day = 1
exact command
```

---

# 31. DEFINITION OF DONE

- [ ] v14 usata come master;
- [ ] vecchie liste usate solo come cross-check;
- [ ] current `sources.yaml` confrontato per dominio;
- [ ] nessuna fonte duplicata;
- [ ] Tier 1 audit completo;
- [ ] Tier 2 mirato auditato;
- [ ] problemi classificati;
- [ ] max 15 nuove fonti abilitate;
- [ ] solo READY promosse;
- [ ] social non scrapati;
- [ ] no browser headless;
- [ ] no backfill massiccio;
- [ ] pipeline testata end-to-end;
- [ ] test suite verde;
- [ ] profilo/comando 1×/giorno pronto;
- [ ] report finale creato;
- [ ] status docs aggiornati.

---

# 32. STOP CONDITION

Al termine:

```text
STOP
```

NON:

```text
registrare scheduler Windows
aumentare frequenza
aggiungere scraper social
aggiungere API esterne
costruire Alert/Case/Task
```

---

# 33. MODALITÀ CLAUDE CODE

Procedere:

```text
READ CURRENT SOURCES
→ READ V14
→ DOMAIN DIFF
→ TEST TIER 1
→ TEST TIER 2 MIRATO
→ CLASSIFY PROBLEMS
→ ADD ONLY READY (MAX 15)
→ RUN PIPELINE
→ CREATE DAILY 1× PROFILE
→ TEST ONCE
→ REPORT
→ STOP
```

Regole:

```text
NO OVERENGINEERING
NO OVERTHINKING
NO MASS IMPORT
NO BLIND MERGE
NO SOCIAL SCRAPING
NO SECOND PIPELINE
NO INVENTED SOURCE IDs
NO INVENTED POLITICAL METADATA
```

Se non verificabile:

```text
MANUAL_REVIEW
```

e proseguire.

---

# RISULTATO ATTESO

Alla fine MEDIA PILOT deve avere:

1. più fonti reali ma non troppe;
2. nessun duplicato per dominio;
3. un elenco preciso delle fonti non integrabili e del perché;
4. una pipeline ancora verde;
5. massimo 15 nuove fonti;
6. scraping web/RSS prudente;
7. social conservati come metadata;
8. un profilo temporaneo per raccogliere tutte le fonti **una volta al giorno**;
9. dati sufficienti per decidere successivamente se aumentare frequenza.
