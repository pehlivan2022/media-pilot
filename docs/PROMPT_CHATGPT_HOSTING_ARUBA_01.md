# Prompt per ChatGPT — mettere Media Pilot online su Aruba.it

Copia tutto quello che sta sotto la riga e incollalo in ChatGPT.

---

## Ruolo

Sei un sysadmin/DevOps che conosce l'offerta di **Aruba.it** (hosting e cloud) e sa portare online
un progetto Python + sito statico. Guidami **passo passo** fino al primo run automatico funzionante.
Voglio comandi concreti e indicazioni su dove cliccare nel pannello, non teoria generale.

**Regole per te:**
- Verifica nomi dei prodotti, limiti e prezzi sull'offerta Aruba **attuale**. Se non sei sicuro di
  un nome commerciale o di un limite tecnico, scrivi *"da verificare sul sito Aruba"* invece di
  inventarlo. Preferisco un buco dichiarato a un dettaglio sbagliato.
- Se ti serve un dato che non ti ho dato, **chiedimelo** invece di assumerlo.
- **Non chiedermi mai di incollare API key, password o credenziali.**

---

## Il progetto in breve

**Media Pilot** è un radar di monitoraggio media politico per la Republika Srpska / Bosnia
Erzegovina. Due pezzi:

1. **Uno scraper + pipeline in Python** che una volta al giorno raccoglie articoli da ~33 fonti
   (portali locali, TV, media economici, monitoraggio elettorale), li pulisce, deduplica, li
   raggruppa in cluster, li assegna a entità e temi politici seguiti, calcola un punteggio di
   rilevanza e produce dei file JSON.
2. **Una dashboard web statica** che legge quei JSON e mostra la rassegna, i temi in crescita,
   i segnali, gli attori e i concorrenti.

Oggi gira **tutto sul mio PC Windows**, lanciato dall'Utilità di pianificazione alle 06:00.
Voglio spostarlo online, così gira anche a PC spento e la dashboard è raggiungibile da smartphone.

---

## Vincoli tecnici (misurati sul progetto reale, non stimati)

**Scraper / pipeline**
- Python **3.12**.
- Dipendenze pip: **`feedparser`** e **`trafilatura`** (quest'ultima è la più pesante: si porta
  dietro parser HTML compilati). Tutto il resto è libreria standard — niente Django, niente Flask,
  niente framework.
- Un run al giorno, un solo processo, sequenziale: `collect → clean → dedup → score → trending →
  signals → export`.
- **~1.400–1.500 articoli raccolti per run.**
- Traffico **in uscita** HTTPS verso: i siti delle fonti (dominio `.ba`, `.rs`), `web.archive.org`
  (usato come fallback quando una fonte non risponde) e le API LLM (Anthropic / DeepSeek).
- **Non espone nessuna porta e non ha bisogno di un web server**: scrive solo file su disco.
- Ha bisogno di **cron** (o equivalente) e di poter **installare pacchetti pip**.

**Dashboard**
- HTML + CSS + JavaScript **statici puri**. Nessun build step, nessun npm, nessun PHP, nessun
  database lato web. Si serve come cartella di file.
- Legge i dati da `assets/data/*.json` (~1,9 MB in tutto).

**Dati e storage**
- Cartella progetto: **262 MB**, di cui **257 MB** sono `data/` (archivi storici, baseline, golden
  set — non tutto va necessariamente online).
- Un database **SQLite** da 2,1 MB (`corpus.db`).
- Crescita: **~1.500 righe JSONL al giorno**, più i file derivati.

**Segreti**
- Due API key (Anthropic, DeepSeek) oggi in un file `.env` locale. **Non devono mai finire in una
  cartella servita dal web.**

**Altro**
- Il run va fatto alle **06:00 ora locale di Sarajevo/Banja Luka** (CET/CEST).
- I contenuti sono **materiale politico riservato**: la dashboard non deve essere pubblicamente
  indicizzabile né aperta a chiunque abbia l'URL.

---

## Cosa ho già

- Un **hosting Linux Aruba** già attivo per un altro progetto (un sito WordPress), che amministro
  dal pannello Aruba e dal file manager web del pannello.
- **Domini registrati su Aruba.**
- Non so se quell'hosting basti anche per questo progetto: dimmelo tu.

---

## Cosa voglio da te, in quest'ordine

**1. Scelta del prodotto Aruba.** Tabella comparativa dei prodotti Aruba che potrebbero reggere
questo progetto (hosting Linux condiviso, cloud/VPS, container/PaaS, altro). Per ognuno rispondi
secco a: si può installare Python 3.12 e fare `pip install`? C'è cron? Si possono lanciare processi
che durano minuti? C'è accesso SSH? Quanto costa all'anno, indicativamente? Poi **un verdetto
motivato**, e se un prodotto va escluso spiega **quale requisito preciso** non soddisfa.

**2. L'hosting che ho già basta o no?** Rispondi in modo netto, e se non basta di' esattamente quale
pezzo non regge (l'installazione di `trafilatura`, il cron, la durata del processo, altro).

**3. Architettura consigliata.** Dove gira lo scraper, dove stanno i file statici della dashboard,
e **come i JSON prodotti dallo scraper arrivano alla dashboard** (stesso server? copia via rsync/
scp? repository git? altro?). Se la soluzione richiede due prodotti Aruba diversi, dillo e spiega
come si parlano.

**4. Domini e rerouting.** Come faccio a **puntare altri domini e sottodomini sullo stesso
hosting**: alias di dominio, domini aggiuntivi, redirect 301, record DNS. Quanti ne permette il
piano che mi consigli. Cosa si fa dal pannello Aruba e cosa invece va fatto sui DNS del dominio.
Includi il caso di un dominio **non** registrato in Aruba che deve puntare lì.

**5. Installazione passo passo.** Dal login al pannello fino al primo run automatico riuscito.
Comandi reali in blocchi copiabili, nell'ordine, con cosa devo vedere a schermo per sapere che il
passo è andato bene.

**6. Cron e segreti.** Come si registra il job giornaliero su quel prodotto, come passo le due API
key senza metterle in una cartella web, dove finisce il log del run e come lo leggo da remoto.

**7. Accesso alla dashboard.** HTTPS e certificato su Aruba, e come proteggo la dashboard visto che
il contenuto è riservato: password HTTP (`.htaccess`), restrizione per IP, o altro — dimmi cosa è
realmente supportato sul prodotto che consigli e quale consigli tu.

**8. Backup e crescita dei dati.** Cosa vale la pena caricare online dei 257 MB e cosa può restare
solo sul mio PC. Come faccio i backup. Fra quanto tempo, con ~1.500 righe al giorno, lo spazio
diventa un problema.

**9. Chiusura.** Costo totale stimato del primo anno, e **le tre cose che più probabilmente
andranno storte** in questa migrazione, con come me ne accorgo.

---

## Come voglio le risposte

- **Fermati dopo il punto 2** e aspetta la mia conferma sulla scelta del prodotto prima di
  proseguire con il resto: non ha senso scrivermi la procedura di installazione per un prodotto che
  poi non compro.
- Comandi sempre in blocchi di codice copiabili, uno per riga.
- Quando una cosa si fa dal pannello Aruba e non da terminale, dimmi il percorso dei menu.
- Se un passo può rompere il sito WordPress che ho già su quell'hosting, **avvisami prima**.
