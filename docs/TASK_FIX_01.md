# TASK FIX 01 — riparare la pipeline, nell'ordine giusto

**Rev. 2** — riscritto dopo tre revisioni indipendenti (Claude, Gemini, GPT). Dove convergevano,
hanno corretto l'ordine della rev. 1 e aggiunto un intervento che mancava del tutto.

Il pilot di `docs/TASK_SCRAPER_PILOT.md` è stato costruito ed eseguito. Il codice gira, i test passano
(14/14), il report era onesto. Ma i meccanismi centrali sono spenti e i risultati inutilizzabili.

Questo task li ripara. **L'ordine è vincolante**: è il risultato di tre analisi che concordavano.

## REGOLE

- Stessi vincoli del task originale: **no overengineering**, dipendenze ferme a `feedparser` +
  `trafilatura`, tutto il resto stdlib. Nessun vector DB, nessun embedding, nessun servizio esterno.
- **Non toccare il frontend.** Nessun file HTML/CSS/JS del progetto.
- **Il testo originale non si traslittera mai.** Le rappresentazioni normalizzate vivono in colonne
  separate (`title_norm`, `text_norm`) e servono solo a confrontare. Una revisione proponeva di far
  girare tutta la pipeline in latino: **no**, si perde la fonte. Si normalizza per confrontare,
  si conserva per mostrare.
- Ogni fix chiude con il suo test e **il suo numero prima/dopo**. Un fix senza numero è un'intenzione.

---

## LE PROVE

Numeri estratti direttamente dai file della prima run, non dal report.

```
293 raw → 245 puliti → 244 item dopo dedup → 240 cluster
dimensione cluster:  {1 articolo: 236,  2 articoli: 4}

item con almeno un protagonista:  117 / 244
protagonista più frequente:       "Predsjedništvo BiH", 49 hit su 244

"Трагедија у БиХ: Пчела усмртила мушкарца"  →  modules: ['predsjednistvo']
"Срамотан призор у БиХ: Ријеком тече крв?"  →  modules: ['predsjednistvo']

top 5 cluster per signal_score:
  2.93  Minić apre il Festival dei prodotti locali
  2.63  Nessun referto dall'Aja sul generale
  2.60  Il leader dei pensionati rivela la sua pensione
  2.33  Una vespa uccide un uomo
  2.33  Sangue nel fiume?

copertura temporale reale (finestra richiesta: 7 giorni):
  RTRS 100 art → 1 giorno · Srpskainfo 50 → 1 giorno · SNSD 10 → 1 giorno
  Banjaluka24 20 → 2 gg · Glas Regije 10 → 2 gg · ATV 100 → 5 gg · Pod lupom 3 → 3 gg

RTRS + ATV = 200 articoli su 293 (68% del corpus), entrambe Banja Luka, owner_group: null
385 errori HTTP 400 su 388, tutti su URL "http://host:443/path"
```

**Questi quattro problemi non sono indipendenti: sono una cascata.** Tutte e tre le revisioni lo hanno
detto con parole diverse. Le entità sporche inquinano i cluster; i duplicati non visti gonfiano gli
eventi; i cluster da un articolo azzerano ogni metrica; e sotto a tutto c'è un corpus di un giorno,
per metà non politico.

---

## FIX 0 — Il golden set, prima di scrivere codice · BLOCCANTE

> **Questo fix ha un task dedicato: `docs/TASK_FIX_00_GOLDEN.md`.** Eseguirlo per primo e tornare qui.
> Automatizza l'annotazione con doppio modello indipendente e lascia all'umano solo i disaccordi più
> un controllo a campione. La sezione qui sotto resta come specifica di *cosa* deve contenere il
> golden set; il *come* sta nell'altro file.

**Perché è il primo.** Le soglie attuali (dedup 0.90, clustering 0.35) sono state scelte senza alcuna
evidenza. I 14 test unitari passano ma non dicono nulla sui dati veri. Senza un golden set, ogni
modifica dei prossimi fix — anche giusta — è un tiro al buio.

Correggo qui una mia regola della rev. 1: avevo scritto «non ricalibrare soglie». Sbagliato, e una
revisione me l'ha contestato correttamente. Vale per i **pesi dello `signal_score`**, non per le
**soglie di dedup e clustering**: quelle vanno calibrate adesso, su evidenza.

### Cosa fare

`data/golden/golden_dataset.json`, **100 item**, annotati a mano dal corpus già raccolto,
deliberatamente stratificati:

```
20  politica vera (dichiarazioni, istituzioni, campagna, liste)
20  duplicati: stesso articolo ripubblicato, titolo riscritto
20  stesso evento raccontato da fonti diverse (cluster attesi)
20  cronaca, sport, salute, meteo — nessuna politica  ← casi negativi
10  cirillico e latino sullo stesso soggetto
10  sigle ambigue in contesto NON politico (US Open, BiH generico, "mandat", "finansiranje")
```

Per ogni item: `is_political`, `entities_attese[]`, `duplicate_of`, `cluster_atteso`.

I casi negativi sono la parte che conta. Il golden set da 30 della prima run non li conteneva, ed è
per questo che ha riportato una precision entità di 0.81 quando la realtà è molto peggio.

### Verifica
- 100 item, la distribuzione sopra rispettata entro ±3
- i 4 esempi noti («vespa», «sangue nel fiume», US Open, "mandat" non politico) sono dentro, con
  `is_political: false` e `entities_attese: []`

---

## FIX A-ORA — Avviare l'accumulo, oggi, in parallelo a tutto · P0

**Perché adesso e non dopo.** Le revisioni erano in disaccordo sulla finestra temporale: una diceva
backfill attivo («non puoi aspettare 7 giorni»), una diceva accumulo («i parser d'archivio si rompono
e vanno manutenuti in piena campagna»), una diceva entrambi. Hanno ragione tutte: l'accumulo **richiede
tempo di calendario**, quindi va acceso subito, mentre si lavora agli altri fix. Il consumo dei dati
accumulati è FIX 4.

### Cosa fare

1. `collect.py`: dedup all'append contro **tutti** i file `data/raw/*.jsonl`, non solo quello di oggi.
   Così `collect` gira più volte al giorno senza duplicare.
2. Farlo girare ogni 30–60 minuti (Task Scheduler di Windows va benissimo, non serve un demone).
3. Documentare in `README` del pilot: **il corpus a 7 giorni si ottiene collezionando per 7 giorni.**
   Nessuna run singola può produrlo da feed RSS tappati a 100 entry.

Costa mezz'ora e da quel momento l'orologio corre mentre si lavora al resto.

### Verifica
- `collect` due volte di fila → zero item aggiunti la seconda volta
- dopo 24h: `data/raw/` contiene più di un file e il conteggio cresce

---

## FIX 1 — Filtro di rilevanza + entity matching · P0

**Tre revisioni su tre hanno indicato questo come primo intervento**, e una ha aggiunto il pezzo che
mancava completamente nella rev. 1: **il filtro di rilevanza politica**.

### 1a — Il filtro che mancava

Metà del corpus è cronaca, sport, salute, meteo. Oggi entra tutto nella pipeline e viene taggato,
clusterizzato, misurato. Migliorare i meccanismi senza questo filtro significa solo rendere più
efficiente l'ingestione di rumore.

Prima dell'entity matching, un filtro deterministico:

- l'articolo passa se contiene **un alias forte** (nome proprio di un protagonista), **oppure**
  almeno **due termini del dizionario di dominio politico** (`izbori`, `stranka`, `kandidat`,
  `poslanik`, `vlada`, `skupština`, `mandat`, `koalicija`, `glasanje`, `lista`, `sjednica`, …)
- gli scartati **restano in archivio** (servono per la baseline e per il RAG), ma **non entrano nel
  ranking politico** e non generano cluster

Non è un filtro AI. È una lista in `config/topics.yaml` e una funzione.

### 1b — Gli alias, in tre classi

Il bug: `Predsjedništvo BiH` viene cercato **token per token**, quindi basta `BiH`, che compare in un
titolo su due. Da qui 49 hit e la vespa presidenziale.

Tre classi, non due:

| Classe | Esempi | Regola di match |
|---|---|---|
| **Forte** | `Nenad Stevandić`, `Ujedinjena Srpska`, `Draško Stanivuković` | matcha da solo |
| **Frase** | `Predsjedništvo BiH`, `Vijeće naroda`, `Centralna izborna komisija` | solo come **sequenza contigua**, nell'ordine |
| **Ambiguo** | `US`, `SP`, `NF`, `BiH`, `RS` | solo con co-occorrenza di un alias **forte**, o di due termini del dizionario politico |

Termini generici come `mandat`, `finansiranje`, `kompenzacion`, `skener` **non sono alias di entità**:
sono termini tematici. Vanno in `weak_keywords`, usati dal filtro 1a, mai come identificatori.

Due dettagli che una revisione ha colto e vanno implementati:
- **confini di parola espliciti** (`\b`): senza, `US` matcha dentro `usvojen`, `ustav`, `fokus`
- **un'entità forte da sola basta.** «Стевандић је изјавио…» è un articolo politico valido con un solo
  soggetto. La co-occorrenza si richiede **solo** alla classe ambigua, mai alla forte

### Verifica
- `predsjednistvo` sotto i **15 hit** su ~250 item (oggi 49). Se resta sopra, non è risolto
- i 4 casi negativi noti → `modules: []`
- precision entità sul golden set: **obiettivo ≥ 0.90 complessiva, ≥ 0.95 sugli alias forti**
- recall entità ≥ 0.60, e dichiarato: qui la precisione vale più del richiamo
- riportare quanti item il filtro 1a scarta. Atteso: circa metà del corpus

---

## FIX 2 — Dedup e clustering, un solo meccanismo a due soglie · P0

Una revisione ha colto una cosa che avevo trattato male: nel panorama mediatico balcanico, dedup e
clustering **non sono due problemi distinti**. Le agenzie (SRNA, FENA) rilasciano lanci che i portali
ripubblicano cambiando titolo, incipit, e a volte alfabeto. «Stesso articolo» e «stesso evento» sono
la stessa funzione a due soglie diverse.

### 2a — Una rappresentazione di confronto sola

In `clean.py`, `text_norm` e `title_norm` diventano: Unicode NFC → minuscolo → cirillico serbo
traslitterato in latino con tabella deterministica → punteggiatura via → stopword serbe molto comuni via.

**L'originale resta intatto e continua a essere ciò che si mostra e si salva.**

### 2b — Dedup sul corpo, non sul titolo

Oggi: `content_hash` → titolo identico → `SequenceMatcher(titolo) ≥ 0.90` entro 48h. Nessun confronto
sul corpo. Risultato: 1 duplicato su 245.

La cascata corretta: URL canonicale → hash esatto → **similarità del corpo** → titolo.
Il corpo diventa il criterio centrale.

Implementazione, senza dipendenze: **shingle di n-gram di caratteri (n=4 o 5)** sul `text_norm`
dei primi ~1500 caratteri, similarità Jaccard. Gli n-gram di caratteri reggono le variazioni di
titolo e le differenze di alfabeto senza tokenizzazione né lemmatizzazione.

Soglia di partenza suggerita dalle revisioni: **0.70**. Va in `config/scoring.yaml` come
`dedup.body_similarity_threshold` e **si calibra sul golden set del FIX 0**, non si adotta al buio.

Se il confronto O(n²) supera i 10 secondi su ~300 item, indicizzare per shingle prima di confrontare.

### 2c — Clustering: prove multiple, e il cluster ha una sua rappresentazione

Tre difetti nel codice attuale, tutti da correggere:

1. **Le entità non vengono usate**, nonostante il docstring dica il contrario: la funzione confronta
   solo la sovrapposizione di token fra titoli
2. **Jaccard 0.35 su titoli interi** è troppo severo per titoli riscritti
3. **Il candidato viene confrontato solo con il primo articolo del cluster**, mai con gli altri membri:
   se A~B e B~C ma A≁C, C resta fuori, e l'ordine di arrivo decide il risultato

Il clustering deve essere **più permissivo del dedup** e combinare più prove con un punteggio
deterministico, non con un singolo test:

- vicinanza temporale
- **entità condivise** (almeno 2)
- n-gram del corpo sopra soglia (partenza suggerita 0.50, da calibrare)
- parole informative condivise, località, numeri, date

E soprattutto: **il cluster accumula una rappresentazione propria** — l'unione delle entità e dei
termini significativi dei suoi membri — contro cui si confronta ogni nuovo candidato.

Che il meccanismo di base funzioni è già dimostrato: `Минић у Бањалуци отворио девети Фестивал
домаћих производа` è stato unito a `Minić otvorio Festival domaćih proizvoda u Banjaluci`.
Cirillico e latino si agganciano. Non servono embedding per risolvere il problema di base.

### Verifica
- dedup: numero di gruppi prima/dopo. Se resta sotto i 10 gruppi su ~250 item, spiegare perché
- clustering: distribuzione delle dimensioni prima/dopo (oggi `{1: 236, 2: 4}`)
- precision clustering sul golden set: **≥ 0.90, anche sacrificando il recall.**
  Meglio due cluster separati dello stesso evento che due eventi politici diversi fusi insieme
- test: due articoli, titoli diversi, primo paragrafo uguale → 1 item, 2 evidence
- test: A~B, B~C, A≁C → un solo cluster da 3, non due

---

## FIX 3 — Indipendenza delle fonti, non conteggio delle testate · P1

**Due revisioni su tre hanno indicato questo come il rischio più serio non nominato.** Nella rev. 1
era a P2, sepolto in fondo. Sbagliato.

### Il problema

RTRS + ATV sono 200 articoli su 293, il 68% del corpus, entrambe emittenti di Banja Luka, entrambe con
`owner_group: null`. `source_diversity` — una delle metriche centrali dello `signal_score` — le conta
come **due conferme indipendenti**.

Il rischio vero, formulato da una revisione: in Republika Srpska la presenza online è fortemente
asimmetrica. I portali ad alto volume seguono la narrativa della maggioranza; opposizione e società
civile pubblicano molto meno e spesso fuori da RSS. Una metrica basata sul volume grezzo trasforma
la dashboard in **un amplificatore dell'agenda di chi ha l'ufficio stampa più grande**, e i segnali
deboli ma critici spariscono. Per un radar di campagna è il fallimento peggiore possibile: non mostra
la temperatura politica, mostra il volume di fuoco.

### Cosa fare

1. **`owner_group`** compilato a mano per le fonti attive — sono dieci righe. Dove la proprietà non è
   accertabile da fonte pubblica, lasciare `null` **e dichiararlo nel report**, mai riempirlo per simmetria.
2. **`origin_type`**: distinguere `agency_repost` da `original_reporting`. Cinque portali che rilanciano
   lo stesso comunicato SRNA non sono cinque conferme.
3. `source_diversity` conta **gruppi editoriali distinti**, non `source_id`.
4. **Quote per fonte nelle metriche aggregate.** Non serve scaricare meno da RTRS e ATV: serve che
   due emittenti non definiscano da sole cosa è "trending". Un tetto al contributo per gruppo nel
   calcolo di velocity e trending.

### Verifica
- test già previsto: due fonti con lo stesso `owner_group` non fanno salire `source_diversity`
- ricalcolare i top cluster: **se il punteggio massimo scende, è il comportamento corretto**
- nel report: contributo percentuale di ogni gruppo editoriale al corpus

---

## FIX 4 — Backfill e onestà delle metriche temporali · P1

Ora che l'accumulo gira da giorni (FIX A-ORA), si chiude la finestra.

1. **Backfill solo da `sitemap.xml`**, dove esiste ed espone `<lastmod>`: si scorre indietro fino a
   7 giorni e si scaricano gli URL con `trafilatura`.
   **Non scrivere parser di paginazione su misura per ogni testata.** Una revisione insisteva su
   questo ed è la posizione giusta per una campagna: gli archivi HTML cambiano struttura, i parser si
   rompono, e la manutenzione ricade su una persona sola nel momento peggiore. Dove non c'è sitemap
   stabile, si dichiara e si vive con l'accumulo.
2. **`window_actual_days`** per ogni fonte in `sources.yaml` e nel report: giorni distinti realmente
   coperti. Mai più scrivere "7 giorni" quando è uno.
3. In `score.py`: se `window_actual_days < 3`, `velocity` e `novelty` sono **`null`**, non 0, e il
   payload porta `baseline_incomplete: true`. Zero è un'informazione falsa; `null` dice "non misurabile".

### Verifica
- tabella fonte → giorni coperti → item, nel report
- nessuna metrica temporale valorizzata dove la baseline non c'è

---

## FIX 5 — Le due cose piccole · P2

**5a — RTRS, 385 errori.** Il feed pubblica `http://www.rtrs.tv:443/vijesti/vijest.php?id=…`:
scheme `http` su porta 443, il server risponde 400. Persi 48 item della TV pubblica, la fonte tier-1
più importante. In `clean.py`, due righe: porta 443 → `https` e porta rimossa; porta 80 → `http` e
porta rimossa. È lavoro del normalizer, non un bug da lasciare alla fonte.

**5b — Sono 7 fonti, non 10.** Le tre `READY_HTML` (Transparency BiH, BN, Dobojski.info) hanno zero
item: verificate in audit, ma senza parser di listing. E l'audit si è fermato a 14 candidati perché
aveva raggiunto quota 10 — fuori restano Glas Srpske, Nezavisne novine, Capital, Klix, N1 BiH, Buka,
Istinomjer. È colpa dell'istruzione originale «fermarsi a 10»: era sbagliata.

Rilanciare `sources.py` su **tutti** i candidati tier-1, senza quota. Scrivere il parser per le tre
HTML una per volta, con fixture. Se una è troppo fragile, marcarla `MANUAL_ONLY` e dichiararlo:
meglio 9 fonti vere che 10 di cui 3 vuote.

### Verifica
- RTRS: zero errori 400, item clean saliti da 52
- ogni fonte `enabled: true` consegna item, oppure è disabilitata con motivo scritto

---

## COSA NON FARE

**Non toccare i pesi di `signal_weights`.** Questa parte della rev. 1 resta valida e le revisioni la
confermano: i cluster in cima oggi (un festival, una vespa, un fiume) non sono un difetto dei pesi,
sono il risultato della cascata. Calibrarli adesso significa adattarli al rumore e rifarli dopo.
Si toccano quando FIX 1, 2 e 3 sono chiusi e misurati.

*(Le **soglie** di dedup e clustering sono un'altra cosa: quelle si calibrano subito, sul golden set
del FIX 0. Vedi la correzione in testa a quel fix.)*

**Non introdurre embedding, vector DB o LLM nel clustering.** Tutte e tre le revisioni concordano che
non serve: gli n-gram di caratteri risolvono il cross-alfabeto senza dipendenze. Se dopo la
calibrazione la precision resta sotto 0.90, allora se ne riparla — con il costo di manutenzione
messo per iscritto.

**Non riscrivere la pipeline.** Il codice è pulito e testato. Il problema è nei meccanismi.

**Non toccare la dashboard.**

---

## FILE

**Modificare**
```
pilot/collect.py     dedup all'append su tutti i raw/*.jsonl; backfill da sitemap; window_actual_days
pilot/clean.py       porta 443/80 nell'URL; text_norm/title_norm con traslitterazione + stopword
pilot/entities.py    tre classi di alias, confini \b, weak_keywords, filtro di rilevanza
pilot/dedup.py       shingle n-gram sul corpo; clustering a prove multiple con centroide di cluster
pilot/score.py       velocity/novelty null se baseline incompleta; source_diversity per owner_group; quote
pilot/sources.py     nessuna quota a 10; parser di listing per le fonti HTML
config/sources.yaml  owner_group, origin_type, window_actual_days
config/scoring.yaml  dedup.body_similarity_threshold, clustering.* — calibrate sul golden set
pilot/test_pipeline.py
```

**Creare**
```
config/topics.yaml                dizionario di dominio politico per il filtro di rilevanza
data/golden/golden_dataset.json   riscritto a 100 item stratificati
data/fixtures/                    una fixture per ogni fonte HTML nuova
```

**Non toccare:** nessun file del frontend.

---

## DEFINITION OF DONE

- [ ] golden set 100 item, stratificato come da FIX 0, con i casi negativi noti
- [ ] `collect` gira a intervalli, due run di fila → zero duplicati
- [ ] filtro di rilevanza attivo: quanti item scarta, dichiarato
- [ ] `predsjednistvo` sotto 15 hit su ~250; i 4 casi negativi → `modules: []`
- [ ] precision entità ≥ 0.90 complessiva, ≥ 0.95 sugli alias forti, sul golden set
- [ ] dedup: gruppi trovati, prima/dopo
- [ ] clustering: distribuzione delle dimensioni prima/dopo; precision ≥ 0.90
- [ ] `owner_group` e `origin_type` compilati o dichiarati non accertabili, fonte per fonte
- [ ] `source_diversity` conta gruppi, non source_id
- [ ] `window_actual_days` per fonte; `velocity`/`novelty` sono `null` dove non misurabili
- [ ] RTRS: zero errori 400
- [ ] `pytest` verde, nessun file del frontend modificato
- [ ] **`signal_weights` invariati**

## LA METRICA CHE DECIDE

Tutte e tre le revisioni convergono su un solo criterio di usabilità, e questo è il collaudo finale:

> **Almeno 8 dei 10 cluster con il punteggio più alto devono essere notizie politicamente rilevanti
> per la campagna.**

Se un analista apre il radar e trova cronaca nera o sport fra i primi risultati, smette di usarlo
entro due giorni. Oggi siamo a 1 su 5.

Nel report finale, elencare i **primi 10 cluster con titolo e punteggio**, e dire onestamente quanti
sono rilevanti. Se in cima c'è ancora una vespa, dirlo — non aggiustare i pesi per nasconderla.

## REPORT FINALE

Un solo report alla fine. Per ogni FIX: `DONE / PARTIAL / FAILED`, **con il numero prima e dopo**.
E in fondo: cosa non ha funzionato, quali soglie sono ancora a occhio, quali fonti restano perse.
