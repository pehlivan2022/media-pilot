# TASK FIX 00 — Golden set semi-automatico

Prompt per Claude Code. **Da eseguire prima di `docs/TASK_FIX_01.md`**, che lo dà per fatto.

Obiettivo: portare l'annotazione di 100 articoli da ~4 ore di lavoro manuale a **~40 minuti di sole
decisioni**, senza che il golden set perda validità.

---

## LA TRAPPOLA, PRIMA DI TUTTO

Un golden set annotato dallo stesso modello che poi viene valutato **non misura la verità**: misura
quanto il sistema somiglia al modello. Il numero che ne esce è privo di significato, e sembra ottimo.

Questo task è costruito attorno a quel problema. Tre difese, tutte obbligatorie:

1. **Doppia annotazione indipendente.** Due modelli diversi (Anthropic e DeepSeek, le chiavi sono già
   in `.env`) annotano lo stesso item **senza vedere la risposta dell'altro**. Dove concordano,
   l'etichetta è provvisoriamente accettata. Dove divergono, va all'umano.
2. **Campione di controllo sugli accordi.** L'umano rivede comunque il **20% degli item su cui i due
   modelli concordano**, scelto a caso. Serve a intercettare l'errore condiviso: due modelli che
   sbagliano allo stesso modo sono invisibili al criterio dell'accordo.
3. **Nessuna annotazione derivata dalla pipeline.** Le etichette non possono venire da `entities.py`,
   `topics.yaml` o `dedup.py`. Se il golden set nasce dalle regole che deve giudicare, non giudica
   niente. Un solo caso ammesso e circoscritto: la **generazione di coppie candidate** (§3), dove
   serve solo a non confrontare 4.950 combinazioni.

Se una di queste tre salta, il golden set è carta straccia e i numeri del FIX 01 non valgono.

---

## COSA È AUTOMATICO E COSA RESTA UMANO

| Fase | Chi |
|---|---|
| Campionamento e stratificazione dei 100 item | automatico |
| Prima annotazione (`is_political`, entità, gloss italiano) | 2 modelli, indipendenti |
| Generazione delle coppie candidate da giudicare | automatico, soglia larga |
| Giudizio sulle coppie (duplicato / stesso evento / diversi) | 2 modelli, indipendenti |
| **Decisione sui disaccordi** | **umano** |
| **Controllo a campione sugli accordi (20%)** | **umano** |
| Calcolo dell'agreement e scrittura del golden set | automatico |

Attesa realistica: su 100 item i due modelli divergeranno su 15–30. Più il 20% di controllo sugli
accordi. **Fanno 30–50 decisioni**, a pochi secondi l'una nella UI di revisione.

---

## 1 — CAMPIONE STRATIFICATO

`python -m pilot.golden sample --n 100`

Dal corpus in `data/clean.jsonl`, campionare con questa distribuzione:

```
20  candidati politici       (contengono un nome proprio di protagonista nel titolo)
20  candidati duplicati      (dal pool delle coppie candidate del §3)
20  candidati stesso evento  (idem, soglia più bassa)
20  candidati non politici   (nessun nome proprio noto, temi di cronaca/sport/salute)
10  cirillico e latino       (stesso soggetto nei due alfabeti)
10  sigle ambigue            (contengono US / BiH / RS / SP / mandat / finansiranje fuori contesto politico)
```

**Attenzione:** questo è solo il criterio di *campionamento*, per assicurare che il golden set contenga
i casi che servono. **Non è l'etichetta.** Un item pescato nella quota "non politici" può risultare
politico all'annotazione, e va benissimo — anzi, è il caso più informativo.

Includere d'ufficio i quattro casi noti della prima run:
`Трагедија у БиХ: Пчела усмртила мушкарца`, `Срамотан призор у БиХ: Ријеком тече крв?`,
l'articolo su "US Open", e un articolo con "mandat" in senso non politico.

Seed fisso, campione riproducibile. Output: `data/golden/sample.jsonl`.

---

## 2 — DOPPIA ANNOTAZIONE INDIPENDENTE

`python -m pilot.golden annotate`

Per ogni item, **due chiamate separate**, una per provider, con lo stesso prompt e senza mai passare
a un modello la risposta dell'altro.

Prompt breve e vincolato, output JSON validato:

```json
{"is_political": true,
 "entities": ["Nenad Stevandić", "NSRS"],
 "gloss_it": "Stevandić annuncia una sessione speciale dell'assemblea sul progetto di legge",
 "confidence": 0.9}
```

Regole nel prompt, esplicite:
- `is_political` = riguarda partiti, candidati, istituzioni, elezioni, campagna, relazioni fra
  soggetti politici. Cronaca nera, sport, salute, meteo, economia generica: **false**.
- `entities` = **solo nomi propri effettivamente presenti nel testo**. Mai dedotti, mai impliciti.
  Se il testo dice solo "BiH" senza riferimento istituzionale, non è un'entità.
- `gloss_it` = **una riga in italiano**. Serve a chi rivede: rende possibile la revisione anche a chi
  non legge il serbo, ed è il motivo per cui questa fase esiste.
- In dubbio: `confidence` bassa. Non indovinare.

Temperatura minima, schema vincolato. Se il parsing fallisce: `REVIEW`, mai un valore riparato a caso.

Output: `data/golden/annotations_a.jsonl` e `annotations_b.jsonl`, mai uniti a questo stadio.

---

## 3 — COPPIE CANDIDATE E GIUDIZIO

100 item fanno 4.950 coppie: non si annotano. Servono candidati.

**Generazione (automatica, soglia deliberatamente larga).** Una coppia entra nel pool se, entro 72h,
la similarità di n-gram di caratteri sul corpo supera **0.35** — una soglia molto più bassa di quelle
in gioco, scelta apposta perché il pool sia largo e non pregiudichi il giudizio.

Questo è l'unico punto dove la pipeline tocca il golden set, ed è ammesso perché serve solo a
*restringere il campo*, non a etichettare. Ma va compensato:

**Campione negativo casuale.** Aggiungere al pool **50 coppie scelte a caso** fra quelle sotto soglia.
Se qualcuna risulta un duplicato o lo stesso evento, il blocking sta perdendo casi — e lo si scopre
adesso, invece che dopo aver calibrato le soglie su un pool cieco.

**Giudizio.** Stessi due modelli, indipendenti, tre etichette secche:

```
DUPLICATO      stesso articolo, ripubblicato o riscritto
STESSO_EVENTO  articoli diversi sullo stesso fatto
DIVERSI        fatti diversi
```

Output: `data/golden/pairs_a.jsonl`, `pairs_b.jsonl`.

---

## 4 — LA UI DI REVISIONE

`python -m pilot.golden review` → apre `http://localhost:8765`

Un `http.server` di stdlib e una pagina HTML sola. Niente framework, niente build, niente dipendenze.
Scrive direttamente su `data/golden/decisions.jsonl` a ogni decisione, così l'interruzione non perde
nulla e si può riprendere.

**Mostra solo ciò che richiede una decisione**, in due code:

```
CODA 1 — DISACCORDI        i due modelli hanno risposto diverso
CODA 2 — CONTROLLO (20%)   i due concordano, campionati a caso
```

Per ogni item, la schermata contiene:
- titolo e primo paragrafo **nell'originale**, cirillico o latino com'è
- il `gloss_it` di entrambi i modelli
- le due risposte affiancate, con la differenza evidenziata
- un link all'URL originale

Tastiera, niente mouse: `1` accetta la risposta A · `2` accetta la B · `3` nessuna delle due, apre un
campo · `spazio` conferma (solo in coda 2) · `←` torna indietro · `s` salta e riprende alla fine.

Barra di avanzamento con il numero di decisioni rimaste. Deve essere possibile chiudere il browser e
riprendere da dove si era.

---

## 5 — CONSOLIDAMENTO E METRICHE DELL'ANNOTAZIONE

`python -m pilot.golden build` → `data/golden/golden_dataset.json`

Ogni etichetta finale porta la sua provenienza:

```json
{"item_id":"…", "is_political":false, "entities":[],
 "label_source":"HUMAN",        // HUMAN | AGREED | AGREED_SPOT_CHECKED
 "models_agreed":true, "reviewed_by_human":true}
```

E un blocco di metriche sull'annotazione stessa, che va nel report:

```
agreement is_political      A vs B, %
agreement entities          Jaccard medio fra i due set
agreement coppie            % di etichette identiche
disaccordi risolti          n
accordi controllati         n   (deve essere ≥ 20%)
errori trovati nel controllo n  ← il numero che conta davvero
coppie sotto soglia risultate positive  ← recall perso dal blocking
```

**Due letture da fare, e da scrivere nel report:**

Se l'**agreement su `is_political` è sotto l'80%**, il problema non sono i modelli: è che la
definizione di "politico" è ambigua. Sistemare la definizione nel prompt e rilanciare, prima di
annotare altro.

Se il **controllo a campione trova errori in più del 10% degli accordi**, il criterio dell'accordo non
tiene su questo dominio: alzare il controllo dal 20% al 50%. È l'unica difesa contro l'errore condiviso.

---

## GUARDRAIL — cosa invalida il golden set

- una sola AI annota, o la seconda vede la risposta della prima
- le etichette provengono da `entities.py`, `topics.yaml` o `dedup.py`
- il controllo a campione sugli accordi viene saltato «perché concordavano»
- nessun campione negativo per il blocking delle coppie
- `label_source` assente: un'etichetta senza provenienza non è verificabile

Se una di queste condizioni si verifica, dichiararlo nel report e **non usare il golden set per
calibrare le soglie del FIX 01**.

---

## FILE

**Creare**
```
pilot/golden/__init__.py
pilot/golden/sample.py       campione stratificato, seed fisso
pilot/golden/annotate.py     doppia annotazione indipendente
pilot/golden/pairs.py        coppie candidate + campione negativo + giudizio
pilot/golden/review.py       http.server stdlib + pagina di revisione
pilot/golden/build.py        consolidamento + metriche di agreement
pilot/golden/review.html     una pagina, niente dipendenze
data/golden/                 sample, annotations_a/b, pairs_a/b, decisions, golden_dataset.json
```

**Modificare:** niente. `pilot/llm.py` esiste già e si riusa così com'è.
Se non gestisce la scelta esplicita del provider, aggiungere solo quel parametro.

**Non toccare:** il frontend, e nessun modulo della pipeline.

---

## DEFINITION OF DONE

- [ ] 100 item campionati con la distribuzione del §1, seed fisso, riproducibile
- [ ] i 4 casi noti della prima run sono dentro
- [ ] due file di annotazione separati, prodotti da provider diversi, nessuno dei due ha visto l'altro
- [ ] pool di coppie candidate + 50 coppie casuali sotto soglia
- [ ] `review` gira offline, salva a ogni decisione, riprendibile dopo la chiusura del browser
- [ ] tutti i disaccordi risolti; **≥ 20% degli accordi controllati a mano**
- [ ] `golden_dataset.json` con `label_source` su ogni etichetta
- [ ] blocco metriche di agreement scritto nel report
- [ ] `.env` fuori dal repo, nessuna chiave nei log

## REPORT

Un solo report alla fine, con:
- quante decisioni umane sono servite davvero, e quanto tempo sono costate
- i tre numeri di agreement
- **quanti errori ha trovato il controllo a campione** — se zero, dire se il campione era abbastanza grande
- quante coppie sotto soglia sono risultate positive, e cosa dice sul blocking
- i casi su cui l'umano ha risposto "nessuna delle due": sono i punti dove la definizione del task
  non è chiara, e vanno riportati per esteso
