# TASK BETA 02 — chiudere la beta di Media Pilot

Scritto il 2026-08-28 dopo la verifica misurata di B0/B1/B2/B4a. Ogni numero qui viene dai file,
non dai report precedenti. Sostituisce la parte non fatta di `TASK_BETA_01.md`.

**Definizione di "beta chiusa"**: la dashboard mostra notizie vere, ordinate in modo difendibile,
aggiornabili con un comando, e ogni soglia del sistema ha accanto il campione su cui è calibrata.
Non "tutti i segnali accesi": alcuni di quei segnali su questo corpus non possono accendersi, e la
beta si chiude dichiarandolo, non fingendolo.

## REGOLE (invariate)

- **No overengineering.** Dipendenze ferme a `feedparser` + `trafilatura`, resto stdlib.
- **Deve funzionare senza LLM.** L'AI è opzionale e va marcata.
- **Zero invenzione.** Dato non verificato = `null`. I campi di giudizio (`risk`, `opportunity`,
  `wedge`, `signal_to_vrh`…) restano ai default: sono a cura umana, non del pilot.
- **Le IJ non sono verificate**: `territory_ij` resta `null`, mai dedotto. Vedi `PROJECT_AUDIT.md` §D.3.
- **Il testo originale non si traslittera mai.**
- Ogni fase chiude con il suo **numero prima/dopo**. Una fase senza numero è un'intenzione.
- Non riscrivere `config/sources.yaml` da zero: `sources.py` lo rigenera e cancella le modifiche manuali.

---

## STATO MISURATO — 2026-08-28

Corpus: **1.627 raw → 1.488 puliti → 1.252 item dopo dedup → 520 rilevanti → 489 cluster**,
17 fonti, 30 giorni civili.

**Fatto e verificato**
- B0 (bug di unità in `velocity`) — chiuso, `test_13`/`test_13b`.
- B4a (Dodik nelle card, alias, filtro `max_document_frequency`) — chiuso.
- B2a (Capital.ba + Dobojski via Wayback CDX) — chiuso.
- B2b Google News RSS — NON_PASSA, dichiarato in `SOURCE_AUDIT.csv`. Non riaprire.
- B2c GDELT — **raggiungibile via `http://`, non `https://`**. Verificato, **non integrato**.
- Filtro temporale (`clean.py: out_of_window`, `STALE_DAYS = 30`) — applicato. 40 item raw
  scartati, `window_actual_days` 56 → 30, `sources.yaml` corretto su 4 fonti.
- `export_dashboard.py` scrive già `assets/data/rassegna.json` con **1.252 item veri e URL veri**
  (backup della demo in `rassegna.json.demo-backup`).
- Test: **19/19**.

**Non fatto, e perché il ranking è piatto**

| | valore |
|---|---|
| `signal_score` | **16 valori distinti su 489 cluster** |
| singoletti | **95,7%** |
| `velocity` | 2 valori (0.0 / 1.0) |
| `novelty` | `None` su 489/489 — hardcoded a `score.py:193` |
| `source_jump` | `True` su 2/489 |
| `entity_centrality` | 4 valori distinti |

Causa isolata e misurata (dettagli in `RFC_SECONDA_OPINIONE_02.md` §8): **la prova di similarità del
corpo usa Jaccard su 4-grammi di caratteri, che non è normalizzato per lunghezza.** Su 16 coppie
cross-fonte a titolo quasi identico (stesso evento certo) dà 0.184–0.374, mentre 2.000 coppie a
caso arrivano a 0.334: **gli insiemi si sovrappongono, nessuna soglia li separa.** Un TF-IDF coseno
scritto in 15 righe di stdlib dà 0.472–0.699 sui positivi contro p95 0.056 sui negativi.

**Escluse con numeri, non riaprirle**: contaminazione date (filtro applicato, non ha spostato
nessuno dei tre criteri di B1), filtro `max_document_frequency` (94,7% senza, e riapre un cluster
da 63), filtro `is_relevant` (94,8% ignorandolo), "le fonti non si sovrappongono" (1.430 coppie
cross-fonte su 218 item).

---

## C0 — Rassegna: due difetti da due righe  ⟶ farlo subito, non dipende da niente

`export_dashboard.py:export_rassegna()` esporta **tutti** i 1.252 item, inclusi i **732 che il
filtro di rilevanza ha scartato**. Misurato: dei 459 item che mappano su una card della dashboard,
**459 su 459 sono rilevanti**. I non rilevanti non portano nulla e diluiscono la rassegna al 58%.

Secondo difetto: `build_rassegna_entry` non esporta **`signal_score`**. Il punteggio si calcola e
non arriva mai alla dashboard, che quindi non può ordinare per rilevanza nemmeno quando il
punteggio funzionerà.

**Cosa fare**
1. Filtrare su `is_relevant` in `export_rassegna()`.
2. Aggiungere `signal_score` (e `cluster_size`) all'entry, prendendolo dal cluster dell'item.
3. Verificare che `radar.js`/`ui.js` siano difensivi sul campo nuovo — **si leggono, non si toccano**.

**Done quando**: `rassegna.json` contiene ~520 item invece di 1.252, la quota con `modules`
valorizzati sale, e ogni entry porta il suo `signal_score`.

### ✅ FATTO il 2026-08-28

`pilot/export_dashboard.py`: filtro `is_relevant`, `signal_score` + `cluster_size` nell'entry,
ordinamento per punteggio decrescente, e una **pagina di prova** `data/rassegna_preview.html`
(autosufficiente, nessuna dipendenza, non è una pagina della dashboard). Test 19/19.

| | prima | dopo |
|---|---:|---:|
| item in `rassegna.json` | 1.252 | **520** |
| con card dashboard | 414 = **33%** | 414 = **80%** |
| con `signal_score` | 0 | **520** |
| ordinati per rilevanza | no | **sì** |

I campi di giudizio restano ai default e `territory_ij` resta `null`: verificato dopo la modifica.

### C0b — 9 card dichiarate senza codici `modules`  ⟶ emerso dalla verifica

106 item rilevanti su 520 non mappano su nessuna card, **e 7 dei primi 20 per punteggio sono fra
questi** — compreso il cluster in cima alla classifica (`signal_score` 7.0, la copertura della morte
di Mladić, entità `predsjednistvo`).

La causa non è che manchino le entità: **32 chiavi su 55 hanno codici `modules`, 23 no.** Le card
esistono in `dashboard-config.js` ma non dichiarano i codici, quindi i loro item sono invisibili.

| chiave senza codici | item rilevanti |
|---|---:|
| `finansiranje` | 147 |
| `doboj` | 123 |
| `predsjednistvo` | 80 |
| `banjaluka` | 39 |
| `sps`, `sp-demos`, `dns-nps`, `josic`, `obren` | 16 / 8 / 7 / 2 / 2 |

**Done quando**: nessuna delle chiavi sopra i 20 item resta senza codici, e la quota di item con
card supera il **90%**. È una modifica a `dashboard-config.js` (frontend, sbloccato da B4), non al
pilot — e va decisa card per card, non con una regola automatica.

---

## C1 — Sostituire la metrica di similarità  ⟶ il vero sblocco

Non è una ricalibrazione: la metrica è quella sbagliata. Tutti i sistemi analoghi (Europe Media
Monitor, NewsCatcher, letteratura sul news story clustering) usano **TF-IDF + coseno su
titolo+corpo dentro una finestra temporale**; nessuno usa Jaccard su n-grammi di caratteri.

**Cosa fare**
1. Scrivere in `pilot/dedup.py` un TF-IDF coseno in stdlib (~15 righe: `df` sul corpus,
   `tf` logaritmico, normalizzazione L2, prodotto scalare sul vettore più corto). Nessuna
   dipendenza nuova, nessun LLM.
2. Sostituire con questo la prova del corpo **sia nel clustering** (`body_overlap_threshold`)
   **sia nel dedup** (`dedup.body_similarity_threshold`). `char_shingles`/`jaccard` restano solo
   se serve un fallback dichiarato.
3. `SHINGLE_MAX_CHARS = 1500` diventa irrilevante per questa prova: il TF-IDF usa tutto il testo.
   Se resta usato altrove, dichiararlo.
4. Costruire il golden set **dal corpus, gratis e senza LLM**:
   - **positivi** = coppie cross-fonte con `title_norm` simile ≥0.85 (stesso evento per costruzione)
   - **negativi** = coppie a caso
   Salvarlo in `data/golden/` come gli altri, con il metodo di estrazione scritto accanto.

**Done quando**: la soglia nuova è scelta sul golden set con **n≥100 coppie** (oggi n=3 per lo
stesso-evento), il commento `# da calibrare` accanto a `body_overlap_threshold` sparisce e riporta
`n=`, e i singoletti scendono **con la precisione misurata**, non solo il conteggio.
Numero di riferimento atteso dalla misura offline: separazione pulita con soglia **0.35–0.45**.

---

## C2 — Ricalibrare il resto, ora che si può misurare

Solo dopo C1: cambiare la metrica sposta tutte le altre soglie.

Nell'ordine, ognuna con `n=` accanto:
`dedup.body_similarity_threshold` → `clustering.body_overlap_threshold` →
`clustering.window_hours` (60, **mai calibrata**) → `clustering.title_overlap_threshold` →
`clustering.max_document_frequency` + `_MIN_ITEMS_FOR_DF` (scelte su un solo corpus).

Rimisurare anche le metriche di FIX_01 sul corpus nuovo: `is_political` (era 83 / 88,9 / 63,2),
precisione entità (94,4% su actor/party), precisione clustering (100% su 49 coppie DIVERSI).
**Un calo qui è informazione, non un fallimento** — va riportato.

Difetto strutturale da chiudere qui, non una soglia: **i passaggi del dedup sono chiusi.** Un item
assorbito in un gruppo al passaggio 2/3 è `used`, quindi il passaggio 4 (titolo ≥0.90) non può più
agganciarlo. Misurato: **12 coppie a `title_norm` identico sopravvivono come item distinti**, tutte
entro 48h, tutte cross-fonte.

**Done quando**: nessuna soglia in `config/scoring.yaml` resta con `# da calibrare`, e le 12 coppie
a titolo identico sono 0.

---

## C3 — Un punteggio onesto invece di cinque segnali finti

Da fare **dopo** C1/C2, con i numeri nuovi in mano. Oggi:

- `novelty`: `None` per costruzione. **Decisione richiesta**: implementarla (serve una baseline
  storica che oggi ha **una sola fonte** su 17 — vedi C4) oppure **toglierla dal punteggio** e
  dichiararlo. Lasciarla come componente sempre `None` è la sola opzione da escludere.
- `source_jump`: `True` su 2/489. Verificare se dipende da `source_type` mal popolato in
  `sources.yaml` o se è davvero raro. Se è davvero raro, non è un segnale di ranking: è un flag.
- `velocity`: tetto strutturale misurato — **8 cluster su 489 hanno mai 2 articoli entro 4h**.
  Dopo C1 rimisurare; se resta sotto ~50 cluster, degradarla a flag binario "sta uscendo adesso"
  invece di tenerla come componente pesata.
- `entity_centrality`: 4 valori distinti. È l'unico segnale che oggi regge il ranking. Verificare se
  è un limite della metrica o delle 54 entità.

**Done quando**: `signal_score` ha **almeno 50 valori distinti** su ~500 cluster (oggi 16), e ogni
componente rimasto ha accanto il numero di cluster su cui varia davvero. Un componente che non
varia esce dal punteggio e viene dichiarato nel report.

---

## C4 — Il backfill che non è mai avvenuto

"30 giorni sulle 17 fonti" non è successo: **una sola fonte copre 28 giorni**, le altre 1–10, e la
mediana di fonti attive per giorno è **3 su 17**. Le fonti solo-RSS danno la finestra del feed.

| fonte | giorni | item |
|---|---:|---:|
| BL_IJ3_002 | 27 | 83 |
| POL_RS_001 | 10 | 111 |
| BL_IJ3_001 | 9 | 148 |
| RS_ENT_002 | 6 | 187 |
| RS_ENT_001 | **2** | 135 |
| BL_IJ3_003 / FBIH_001 / SRC_009 | **1** | 91 / 98 / 95 |

**Cosa fare**: applicare il backfill sitemap/Wayback CDX già scritto alle fonti ad alto volume che
oggi danno 1-2 giorni (`RS_ENT_001`, `BL_IJ3_003`, `FBIH_001`, `SRC_009`, `RS_ENT_002`). Una fonte
per volta, con pausa fra le richieste: Wayback è un servizio pubblico gratuito.

Nota misurata, da non aspettarsi troppo: sulla fetta più densa (12 fonti attive) i singoletti sono
92,7% contro 98,3% sulla storia sottile. La larghezza vale ~6 punti, **non è il fattore principale**
— quello è C1.

Secondo punto, separato: **`RS_ENT_001` consegna solo il sommario RSS** (mediana 285 caratteri, 79%
sotto 600, contro 1.760 di corpus). O si estrae il testo pieno seguendo il link, o va marcata come
fonte "solo titolo" e trattata di conseguenza nel clustering.

**Done quando**: mediana di fonti attive per giorno ≥ 8 (oggi 3), e nessuna fonte con >80 item
copre meno di 5 giorni.

---

## C5 — GDELT, come strato di scoperta a bassa priorità

Verificato: `http://api.gdeltproject.org` risponde (la 443 no). Query per paese
(`sourcecountry:BK`): 34 articoli, 7 domini, **6 non fra le fonti esistenti**.

**Aspettativa onesta, già misurata**: quei domini sono quasi tutti della Federazione/Sarajevo o
croati. Servono a vedere **come la politica RS viene raccontata fuori dalla RS** — materia da
`source_jump` — e **non densificano la copertura locale RS**. Non aspettarsi che chiuda C1 o C4.

**Done quando**: integrato in `collect.py` come fonte di scoperta (URL + titolo; il testo lo prende
`trafilatura` come per tutto il resto), con la sua riga in `SOURCE_AUDIT.csv`, oppure archiviato con
il motivo. Entrambe le risposte sono accettabili.

---

## C6 — Una run ripetibile, e il freeze della beta

Oggi la pipeline si lancia a mano, in ordine, e sbagliare l'ordine produce numeri falsi (già
successo: `entities` va rilanciato **e poi `dedup`**, non solo `score`, dopo ogni modifica a
`dashboard-config.js`).

**Cosa fare**: un solo entry point che esegua `collect → clean → entities → dedup → score →
export_dashboard` con i conteggi di ogni stadio, e che si fermi al primo stadio che produce zero.
Esistono già `run_retry.bat`/`rerun_retry.bat`: verificare se coprono già questo prima di scrivere
altro.

**Done quando**: un comando solo rigenera tutto dal raw e stampa la catena dei numeri; il report
finale di beta (`docs/BETA_RESULTS.md`) riporta corpus, cluster, distribuzione di `signal_score`,
copertura card, e **l'elenco esplicito di cosa la beta NON fa** (IJ non verificate, campi di
giudizio a cura umana, `novelty` decisa in C3).

---

## ORDINE

```
C0  rassegna (2 righe)         <- subito, indipendente, guadagno visibile
C1  metrica TF-IDF + golden    <- IL blocco: senza questo il ranking resta a 16 gradini
C2  ricalibrazione + dedup     <- dipende da C1
C3  punteggio onesto           <- dipende da C1/C2
C4  backfill fonti solo-RSS    <- parallelizzabile con C1, vale ~6 punti
C5  GDELT                      <- opzionale, bassa priorità
C6  run unica + BETA_RESULTS   <- chiude
```

## LA COSA PIÙ IMPORTANTE

La beta non si chiude quando i cinque segnali sono accesi: due di quei cinque, su un corpus di
media locali della RS, **non possono accendersi**, ed è stato misurato. Si chiude quando il
punteggio ordina le notizie in modo difendibile con i segnali che restano, e quando il documento
finale dice con precisione quali sono e cosa il sistema non sa fare.

Se dopo C1 e C2 `signal_score` ha ancora meno di 50 valori distinti su ~500 cluster, allora il
problema non era la metrica e va riaperta la domanda di `RFC_SECONDA_OPINIONE_02.md` §7: se un
punteggio a più segnali sia recuperabile su questo corpus, o vada ridisegnato.
