# TASK_FINAL_DASHBOARD_BETA_01
## MEDIA PILOT / RADAR POLITICO — Beta Dashboard operativa

**Stato:** READY_FOR_IMPLEMENTATION  
**Priorità:** IMMEDIATA  
**Scope:** FRONTEND / DASHBOARD ONLY  
**Obiettivo:** completare la prima parte del progetto rendendo la dashboard esistente compatta, leggibile e realmente alimentata dai dati del Media Pilot.

---

# 0. RIFERIMENTO VISIVO

Usare come riferimento la demo esistente:

`https://www.skint.org.uk/us-demo-media-pilot/`

La nuova Beta NON deve essere una copia 1:1.

Deve mantenere:
- identità e logica del progetto;
- impostazione da “radar operativo”;
- card/semafori come elemento principale;
- chiarezza immediata;
- leggibilità su desktop e telefono.

Deve migliorare soprattutto:
- compattezza;
- gerarchia visiva;
- spazi;
- leggibilità;
- quantità di informazioni realmente utili;
- navigazione.

Prima di modificare:
1. aprire la demo;
2. leggere i file frontend reali del progetto;
3. verificare quali componenti esistono già;
4. riusare il più possibile;
5. NON riscrivere il progetto da zero.

---

# 1. SCOPO DELLA BETA

La dashboard deve permettere di capire in pochi secondi:

1. **Cosa sta succedendo?**
2. **Chi / cosa sta crescendo di attenzione?**
3. **Quali temi richiedono controllo?**
4. **Quali fonti/articoli costituiscono l'evidence?**
5. **Quando è stato aggiornato il sistema?**

La HOME non deve sembrare:
- un pannello tecnico;
- un foglio Excel;
- una dashboard piena di KPI;
- un sistema di allarmi generici.

Deve sembrare un **radar politico operativo**.

---

# 2. PRINCIPIO VISIVO CENTRALE

## CARD + SEMAFORI IN PRIMO PIANO

I “semafori” sono il componente principale della dashboard.

Ogni card rappresenta una entità / relazione / tema monitorato.

Esempi già esistenti nel progetto:
- US
- STE
- US ↔ SNSD
- SNSD
- Opposizione
- OHR
- CIK / Elezioni 2026
- Doboj
- Beograd
- altri card già presenti in `dashboard-config.js`

NON inventare nuove entità o mapping politici.

Usare solo quelle già dichiarate/configurate.

---

# 3. SEMAFORI — REGOLE BETA

Colori funzionali:

### GRIGIO
Dati insufficienti o nessuna attività recente significativa.

### VERDE
Monitoraggio normale, nessun Signal `REVIEW` rilevante.

### AMBRA
Presenza di uno o più Signal `REVIEW` / aumento significativo da controllare.

### ROSSO
Solo stato umano / Alert confermato.

**NON generare automaticamente ROSSO da Trending o Signal.**

La macchina può portare una card fino ad AMBRA.

Il ROSSO deve restare riservato al workflow umano futuro o a dati già esplicitamente marcati come Alert.

---

# 4. STRUTTURA HOME

La HOME Beta deve essere semplice.

## 4.1 Header compatto

Mostrare:
- MEDIA PILOT / RADAR;
- stato `ONLINE` / errore pipeline;
- ultimo aggiornamento;
- bottone menu;
- eventualmente ruolo attivo se già esiste nel frontend.

Evitare header alto o pieno di pulsanti.

---

## 4.2 Blocco SEMAFORI

Subito dopo l'header.

Layout desktop:
- griglia compatta;
- circa 4–6 card per riga in base alla larghezza;
- card più basse delle attuali;
- stesso linguaggio grafico;
- niente ombre pesanti;
- niente spazi vuoti inutili.

Ogni card mostra solo:

```text
NOME
STATO / COLORE
trend ↑ ↓ →
ultimo cambiamento / breve indicatore
```

Facoltativo, se già disponibile:
- numero eventi 24h;
- numero fonti.

NON mostrare sulla card:
- cosine;
- hash;
- score tecnico;
- cluster id;
- debug;
- lunghe descrizioni.

---

# 5. CLICK SULLA CARD

Il click deve aprire un dettaglio leggibile senza cambiare pagina se possibile.

Preferenza:
- drawer laterale;
oppure
- modal/pannello già esistente.

Contenuto:

```text
Nome card
stato
trend / momentum
ultimi eventi
Signal collegati
ultime notizie
fonti
evidence URL
timeline breve
```

Non inventare contenuti mancanti.

Se un dato non esiste:
- ometterlo;
oppure
- mostrare `—`.

---

# 6. TRENDING

Dopo i semafori:

## “TRENDING ADESSO”

Mostrare massimo **5–8 elementi** in HOME.

Usare il file reale:

`assets/data/trending.json`

Priorità visuale:
1. momentum;
2. unique_sources_24h;
3. unique_events_24h;
4. mentions_24h;
5. recency.

Non mostrare il vecchio `signal_score` come ranking principale.

Ogni riga/card Trending deve essere compatta:

```text
ENTITÀ
+XX% momentum
X eventi · Y fonti
ultimo aggiornamento
```

Click:
→ evidence / eventi / articoli collegati.

---

# 7. SIGNAL

Sezione:

## “DA GUARDARE”

Usare:

`assets/data/signals.json`

In HOME mostrare massimo **3–5 Signal**.

Ogni Signal:

```text
entità / tema
why_now
numero eventi / fonti
classificazione REVIEW
tempo
```

NON mostrare tutti i Signal in HOME.

Prevedere link/bottone:
`Vedi tutti i Signal`

Per la Beta:
- MONITORING = secondario;
- REVIEW = evidenziato;
- nessun P1/P2 automatico;
- nessun Case automatico.

---

# 8. RASSEGNA

Sezione:

## “ULTIME NOTIZIE RILEVANTI”

Usare:

`assets/data/rassegna.json`

Mostrare un elenco compatto con:
- ora/data;
- titolo;
- fonte;
- entità/card;
- eventuale indicatore duplicato/evento solo se utile;
- link originale.

Filtri minimi:
- tempo;
- fonte;
- entità;
- tema.

Non creare un sistema di ricerca complesso in questa fase.

---

# 9. STATO PIPELINE

Usare:

`data/pipeline_health.json`

Mostrare nell'interfaccia soltanto informazioni operative:

```text
ultimo aggiornamento
fonti attive
fonti OK
fonti fallite
nuovi item
durata ultima run
```

In HOME deve essere molto compatto.

Esempio:

`● Online · aggiornato 00:42 · 17/18 fonti OK`

I dettagli tecnici possono aprirsi su richiesta.

---

# 10. MENU COLLASSABILE

Creare / sistemare un menu laterale collassabile.

## Desktop

Stato aperto:
- circa 200–240 px;
- icona + label.

Stato chiuso:
- circa 56–68 px;
- solo icone;
- tooltip o label accessibile.

Il contenuto principale deve espandersi automaticamente.

## Mobile

Menu off-canvas / drawer.

Nessuna sidebar permanentemente visibile sui telefoni.

---

# 11. VOCI MENU BETA

Usare solo sezioni realmente utili.

Ordine suggerito:

```text
RADAR
Rassegna
Trending
Signal
Archivio
Fonti
Stato sistema
```

Se alcune sezioni non sono ancora reali:
- non riempirle con dati DEMO invisibilmente;
- mostrare chiaramente `In sviluppo`;
oppure
- non inserirle ancora nel menu.

Non mescolare dati reali e demo senza indicazione.

---

# 12. DATI REALI DA COLLEGARE

La Beta deve leggere realmente:

```text
assets/data/rassegna.json
assets/data/trending.json
assets/data/signals.json
data/pipeline_health.json
```

Questi sono il cuore della prima versione operativa.

Prima di implementare:
- leggere `docs/dashboard-data-contract.md`;
- verificare gli schema REALI;
- adattare il frontend agli schema esistenti;
- non cambiare arbitrariamente gli output Python per comodità frontend.

---

# 13. DATI DEMO

`alerts.json`
`cases.json`
`tasks.json`
`archive.json`
`candidates.json`

possono essere ancora demo / non consolidati.

Regola:

**non presentarli come dati reali.**

Per questa Beta è accettabile:
- nasconderli;
- disabilitare le relative sezioni;
- marcarle `DEMO` / `IN SVILUPPO`.

Non implementare adesso il workflow completo Alert → Case → Task.

---

# 14. FILE FRONTEND

Prima leggere realmente:
- `index.html`
- `styles.css`
- `app.js`
- `radar.js`
- `ui.js`
- `data.js`
- `dashboard-config.js`
- eventuali `media.html`
- eventuali `vrh.html`

Usare solo quelli realmente presenti.

Non creare copie tipo:
- `index-new.html`;
- `dashboard-v2.html`;
- `final-final.html`;

salvo una preview temporanea chiaramente eliminabile.

L'obiettivo è aggiornare il frontend canonico esistente.

---

# 15. DESIGN

## Aspetto generale

- chiaro;
- moderno;
- compatto;
- professionale;
- “app-like”;
- leggibile;
- poco decorativo.

### Background
Non bianco puro ovunque.

Usare un fondo neutro molto leggero e card distinguibili.

### Card
- bordi sottili;
- radius moderato;
- quasi nessuna ombra;
- padding contenuto;
- altezze coerenti.

### Colori
Usare colore soprattutto per:
- semafori;
- stato;
- trend;
- priorità.

Non colorare inutilmente ogni componente.

### Tipografia
- leggibile;
- buon contrasto;
- numeri e stato ben leggibili;
- label secondarie più piccole ma non microscopiche.

---

# 16. DENSITÀ

La versione attuale va resa più compatta.

Ridurre:
- margini verticali;
- header;
- padding card;
- spazi tra sezioni;
- testi descrittivi ripetitivi.

Ma NON comprimere al punto da rendere difficile la lettura.

Target:
su desktop 1920/1440 deve essere visibile gran parte della situazione senza scroll eccessivo.

---

# 17. RESPONSIVE

Verificare almeno:

```text
390 px
768 px
1280 px
1920 px
```

### Mobile
- semafori 2 colonne se leggibili, altrimenti 1;
- menu drawer;
- niente overflow orizzontale;
- testo e stato leggibili;
- pannelli dettaglio full-screen o quasi.

### Desktop
- sfruttare la larghezza;
- evitare colonna centrale stretta con enormi margini laterali.

---

# 18. LANGUAGE / LABEL

Mantenere la lingua UI già scelta nel progetto:
**serbo cirillico** per label operative dove già previsto.

Non tradurre arbitrariamente:
- ID;
- chiavi JSON;
- nomi codice;
- source_id;
- entity_id.

Codice e variabili restano preferibilmente EN/latino.

---

# 19. PERFORMANCE

La dashboard deve funzionare con JSON statici.

Non introdurre:
- React;
- Vue;
- Angular;
- build system;
- backend API;
- database.

Se il progetto attuale è vanilla HTML/CSS/JS, resta vanilla.

Caricare i JSON una volta e riusare i dati in memoria.

---

# 20. FAILURE STATES

Gestire almeno:

### JSON mancante
Mostrare:
`Dati non disponibili`

### JSON vuoto
Mostrare:
`Nessun dato recente`

### pipeline health con errori
Header/stato:
`DEGRADED`

La dashboard non deve rompersi completamente perché manca un singolo file.

---

# 21. NO HALLUCINATION

Regole assolute:

- non inventare Signal;
- non inventare Alert;
- non inventare valori dei semafori;
- non inventare mapping card;
- non inventare fonti;
- non inventare entità;
- non dedurre alleanze/conflitti;
- non convertire automaticamente Trending in rischio politico;
- dati mancanti = null / assenti.

---

# 22. TEST FRONTEND

Aggiungere test/smoke check coerenti con il progetto esistente.

Verificare:

1. dashboard carica senza errori JS;
2. `rassegna.json` viene letto;
3. `trending.json` viene letto;
4. `signals.json` viene letto;
5. `pipeline_health.json` viene letto;
6. semafori renderizzati;
7. menu collapse funziona;
8. menu mobile funziona;
9. detail card apre/chiude;
10. evidence link apre URL originale;
11. assenza di un JSON non rompe tutto;
12. niente dati demo spacciati per reali;
13. nessun ROSSO automatico da Signal/Trending.

---

# 23. DEFINITION OF DONE

La Beta Dashboard è conclusa quando:

- [ ] la dashboard canonica è stata aggiornata;
- [ ] il layout è più compatto della demo precedente;
- [ ] i semafori sono l'elemento principale;
- [ ] menu laterale collassabile desktop;
- [ ] menu drawer mobile;
- [ ] `rassegna.json` reale collegato;
- [ ] `trending.json` reale collegato;
- [ ] `signals.json` reale collegato;
- [ ] `pipeline_health.json` reale collegato;
- [ ] massimo 5–8 Trending in HOME;
- [ ] massimo 3–5 Signal in HOME;
- [ ] click semaforo → dettaglio/evidence;
- [ ] nessun dato inventato;
- [ ] nessun ROSSO automatico;
- [ ] nessun framework nuovo;
- [ ] nessuna regressione della pipeline;
- [ ] responsive verificato;
- [ ] console browser senza errori;
- [ ] dati DEMO separati chiaramente dai REAL;
- [ ] documentazione aggiornata.

---

# 24. OUTPUT DOCUMENTAZIONE

Creare:

```text
docs/TASK_FINAL_DASHBOARD_BETA_01_RESULTS.md
```

Con:

- file modificati;
- componenti riusati;
- componenti rimossi/semplificati;
- JSON reali collegati;
- regole semafori;
- comportamento menu;
- responsive testato;
- errori/limiti;
- screenshot o descrizione delle viste;
- eventuali cose lasciate per fase successiva.

Aggiornare:

```text
docs/FINAL_PROJECT_STATUS.md
```

---

# 25. NON FARE IN QUESTO TASK

NON implementare:

- repository scraper/API esterni;
- nuove fonti;
- altro backfill;
- modifiche dedup;
- modifiche clustering;
- modifiche TF-IDF;
- modifiche `signal_score`;
- taratura Signal;
- Windows Task Scheduler definitivo;
- API backend;
- database;
- Archive completo;
- Alert workflow completo;
- Case;
- Task;
- Decision.

Questi vengono DOPO la Beta Dashboard.

---

# 26. PROSSIMO TASK DOPO QUESTA BETA

Quando questa dashboard è operativa e verificata:

```text
TASK_EXTERNAL_SCRAPER_REPOS_01
```

Scopo:
auditare e integrare in modo controllato repository GitHub / scraper / API esterni già esistenti, senza riscrivere il collector MEDIA PILOT.

NON iniziarlo durante questo task.

---

# 27. MODALITÀ DI LAVORO CLAUDE CODE

Procedere autonomamente:

```text
READ
→ PLAN breve
→ IMPLEMENT
→ TEST
→ FIX
→ TEST
→ REPORT
→ STOP
```

Non chiedere conferma per micro-decisioni tecniche.

Se un dato politico/mapping non è dimostrabile:
`KEEP_NULL / REVIEW`.

Non over-engineering.

Non riscrivere ciò che funziona.

---

# RISULTATO ATTESO

Alla fine di questo task devo poter:

1. lanciare la pipeline esistente;
2. aprire la dashboard;
3. vedere subito lo stato del radar;
4. capire quali card sono verdi/ambre/grigie;
5. vedere cosa è Trending;
6. vedere i pochi Signal da controllare;
7. aprire evidence e articoli;
8. usare il menu in modo compatto;
9. usare la dashboard anche da telefono.

Questa è la **prima Beta realmente utilizzabile del MEDIA PILOT**.
