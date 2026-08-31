# TASK — FASE 3, prossimi passi Media Pilot

**Repo:** `C:\Users\frontofficedx\Desktop\media-pilot` (branch `master`)
**Scritto:** 2026-08-31 04:10 UTC, da una sessione esterna che ha verificato tutto via `gh` e `git show`
**Predecessore:** `docs/TASK_FASE2_COMPLETAMENTO.md` — TASK A, C, D eseguiti (commit `923cde1`),
TASK B eseguito (cron disattivato, `da513a6`), TASK E **non eseguito e mal diagnosticato** (vedi §2).

---

## 0. PRIMA DI TUTTO

```bash
git add docs/TASK_FASE3_NEXT.md && git commit -m "Add FASE 3 next-steps task"
```

**Mai `git clean -fdx` in questo repo** — il 31/08 ha cancellato `data/raw/`, `errors.jsonl` e
`.env` in modo irreversibile. `data/golden/` e `data/fixtures/` sono ora tracciati (TASK C fatto),
ma `data/raw/` no: vive solo sul branch `runtime-state`.

---

## 1. STATO ALLE 04:10 UTC

| | |
|---|---|
| Cron | **disattivato** (`daily-pipeline.yml`, commentato in `da513a6`) — nulla parte da solo |
| TASK A (fix incrementale) | implementato in `923cde1` come variante **A1**, test 26/26 verde |
| TASK C (`golden/`+`fixtures/` in git) | fatto |
| TASK D (`items_fetched`/`items_written`) | fatto |
| Run Actions post-fix `33355679965` | **ancora in corso a 7m00s** al momento della scrittura |

**Prima cosa da fare:** leggere l'esito di quel run.

```bash
gh run view 33355679965 --json status,conclusion,jobs
git show origin/master:data/pipeline_health.json | python -c "import json,sys; d=json.load(sys.stdin); print({k:d[k] for k in ('duration_sec','items_fetched','items_written')})"
```

Criterio del TASK A: `duration_sec` sotto i 600. A 7 minuti era già 7× meglio dei 55, ma il
numero finale non è stato osservato da nessuno.

---

## TASK F — Completare il fix incrementale: A1 copre solo 6 fonti su 25 (priorità 1)

La condizione implementata è `window_actual_days < days` (7). Misurata su `config/sources.yaml`:

```
fonti RSS totali ......................... 25
  window >= 7  -> SALTANO il supplemento ....  6
  window <  7  -> lo rifanno OGNI run ....... 19
distribuzione: 1gg:4  2gg:6  3gg:3  5gg:3  6gg:3  7gg:6
```

**Il problema è strutturale, non transitorio.** `window_actual_days` misura l'**ampiezza
temporale degli articoli presenti in `data/raw/`**, che dipende da quanto indietro va il feed
RSS della fonte — non da "abbiamo già questi URL".

Caso che lo dimostra: **`RS_ENT_001` (RTRS) ha `window_actual_days: 2`** pur pubblicando ~100
articoli al giorno. Il suo feed espone solo le ultime ~24-48 ore, quindi il valore **non
raggiungerà mai 7** e RTRS rifarà il supplemento a ogni run, per sempre. Stessa sorte per
`BL_IJ3_006`, `BL_IJ3_007`, `FBIH_001`, `FBIH_003` (window=1).

Le fonti locali a basso volume — quelle per cui il supplemento serve meno — sono esattamente
quelle che non supereranno mai la soglia.

**Fare: la variante A2**, già descritta in `TASK_FASE2_COMPLETAMENTO.md` §A2 e già predisposta
nel codice. `collect_from_sitemap_backfill()` accetta `exclude_canonical` (`collect.py:147`) e
non lo riceve mai popolato. Passare lungo la catena
`collect()` → `collect_supplemental_history()` → `collect_from_sitemap_backfill()`
l'insieme dei `final_url` canonici già presenti in `data/raw/*.jsonl`.

Nota di efficienza: la scansione di tutti i raw è già fatta a ogni run per il dedup in scrittura
(`collect.py:462-466`) e misurata in **0,52 s su 1808 righe** — spostarla prima del ciclo e
riusarne il risultato non costa nulla.

Tenere A1 come guardia aggiuntiva: le due condizioni sono complementari, non alternative.

**Criteri di accettazione:**
- Numero di fonti che saltano il supplemento: da 6/25 a ≥20/25 (stamparlo).
- `duration_sec` su Actions sotto i 600 con storia piena.
- Righe scritte in `data/raw/<oggi>.jsonl` invariate rispetto a un run senza la modifica su
  almeno 3 fonti campione, incluse RTRS e una locale a basso volume: **nessun articolo perso**.
- `python -m pilot.test_pipeline` verde, con un test nuovo sul filtro `exclude_canonical`.

---

## TASK G — Il layer segnali non discrimina nulla (priorità 1)

**Correzione formale**: la sessione precedente ha concluso che «la tesi dei 4 segnali su 5
inerti non regge, si muovono». **La conclusione è sbagliata perché è stata misurata sul file
sbagliato**: sono stati confrontati `mentions_24h`, `momentum`, `unique_sources_24h`,
`acceleration`, che sono i campi numerici di `trending.json`. I 5 segnali sono invece i
**booleani** `confidence_components` in `signals.json`, prodotti da `signals.py:85-89`.

Confronto corretto fra i due run Actions (`261dfdf` → `1c63702`), su 17 entità in comune:

```
momentum        cambia in  2/17 entita
sources         cambia in  0/17
events          cambia in  0/17
salience        cambia in  0/17
cross_entity    cambia in  0/17
classification: REVIEW per 17/17 in ENTRAMBI i run
```

**Quattro componenti su cinque non cambiano mai. La tesi originale era corretta.**

Il motivo, misurato sulle distribuzioni reali in `signals.json` (run `1c63702`):

| componente | soglia in `signals.py` | distribuzione osservata | esito |
|---|---|---|---|
| `cross_entity` | `CO_ENTITY_SIGNAL_MIN = 2` | **min 8**, mediana 17 | **mai falso** — è una costante |
| `salience` | `SALIENCE_SIGNAL_MIN = 1.0` | min 0,75 · **mediana 1,65 = max 1,65** | metrica satura |
| `events` | `EVENTS_SIGNAL_MIN = 2` | **min 2**, mediana 7 | sempre vero |
| `sources` | `SOURCES_SIGNAL_MIN = 3` | min 2, mediana 5 | quasi sempre vero |
| `momentum` | `MOMENTUM_SIGNAL_MIN = 0.5` | **mediana 0,53** | l'unico che discrimina |

Tutte le soglie tranne `momentum` stanno sotto il **minimo** osservato o vicinissime. Il
risultato è che ogni entità che entra in lista accende tutti e cinque i componenti, prende
`classification: REVIEW` e `confidence` ∈ {0,6 · 0,8 · 1,0}. **Il layer segnali non separa
niente**: qualunque analisi costruita sopra erediterebbe questa cecità.

`max_entity_salience` con mediana **uguale** al massimo (1,65) va guardato a parte: sembra
tappato, non distribuito. Verificare in `entity_salience.py` se il valore è limitato per
costruzione.

**Fare, in ordine:**
1. Stabilire dove sta la soglia utile per ciascuna metrica usando `data/golden/` — le
   annotazioni (`annotations_a.jsonl`, `annotations_b.jsonl`, `golden_dataset.json`, ora
   tracciate) sono l'unica verità a terra disponibile. Non ricalibrare a occhio.
2. Ritarare le 5 costanti `*_SIGNAL_MIN` in modo che i componenti si accendano su una minoranza
   di entità, non su tutte.
3. Se `cross_entity` resta sempre vero anche dopo la taratura, **rimuoverlo**: un componente
   costante è rumore che finge di essere informazione.
4. `classification` deve poter assumere più di un valore, altrimenti va tolto anche quello.

**Criteri di accettazione:** su due run consecutivi, almeno 3 componenti su 5 cambiano stato in
≥1 entità, e `classification` produce ≥2 valori distinti sullo stesso corpus. Documentare la
taratura scelta e il campione golden usato in `docs/SIGNAL_CALIBRATION.md`.

---

## TASK H — Riaccendere il cron (priorità 2, dopo F)

`.github/workflows/daily-pipeline.yml` righe 5-12: blocco `schedule:` commentato.

Riabilitare **solo dopo** che il TASK F ha prodotto un run Actions sotto i 600 s. Prima di
scommentare, chiedere all'utente gli orari: il cron GitHub è UTC fisso e **non segue l'ora
legale**, quindi `0 5` e `0 11` valgono 07:00/13:00 d'estate e 06:00/12:00 d'inverno a Sarajevo.
Gli orari attuali sono un default scelto da un'altra sessione, mai confermato.

Valutare anche se 2 volte al giorno serva davvero: il run 2 del test ha scritto **60 righe
nuove** contro le 1811 del run 1. Se il secondo passaggio quotidiano porta poche decine di
articoli, una volta al giorno può bastare — decisione dell'utente, con il numero in mano.

---

## TASK I — Allargare le fonti (priorità 2, indipendente)

Task separato e già scritto:
`C:\Users\frontofficedx\Desktop\media-pilot-RECUPERO-2026-08-31\TASK_SOURCE_EXPANSION_02.md`

In sintesi: `docs/SOURCE_EXPANSION_AUDIT_01.csv` contiene **13 fonti `READY_NOT_ENABLED_YET`**
— già testate, feed valido, articoli contati, mai scritte in `sources.yaml`. Sei hanno RSS con
10-18 articoli. Vanno ri-verificate prima di abilitarle (l'audit è del 29/08 e almeno
`istraga.ba` risulta ora irraggiungibile).

**Non eseguirlo insieme al TASK F**: aggiungere fonti mentre si cambia la logica di raccolta
rende impossibile capire quale dei due ha causato una variazione nei tempi o negli item.

---

## TASK L — Analisi dei risultati (priorità 3, bloccata da G)

Era il TASK E. **Non iniziare finché il TASK G non è chiuso**: analizzare risultati con un
layer di segnali che classifica tutto `REVIEW` produce un'analisi che dice sempre la stessa cosa.

Quando G è fatto, la domanda da porre all'utente è cosa deve rispondere il prodotto. Opzioni
concrete, da fargli scegliere — non da decidere da soli:
- **Andamento per entità nel tempo** — chi sale e chi scende fra un run e l'altro.
- **Confronto fra testate sullo stesso evento** — chi lo copre, chi lo tace, con quale taglio.
  È l'unico che sfrutta davvero i campi `credibility` / `bias_score` / `manipulation_risk`
  già presenti nel registro fonti.
- **Anomalie per fonte** — una testata che improvvisamente pubblica il triplo, o smette.
- **Digest periodico** — riassunto testuale delle N storie principali.

Solo dopo la scelta: proposta da 1 pagina, approvazione, poi codice.

---

## FUORI SCOPO

- **Niente scraper Facebook/Instagram.** 108 fonti su 110 hanno un sito, **zero** sono
  raggiungibili solo via social. La via legittima per il segnale social è la Meta Content
  Library (sostituta di CrowdTangle, chiuso il 14/08/2024) — richiesta separata, settimane.
- **Niente Scrapling/Playwright** senza il numero misurato di articoli/settimana che
  porterebbero le 5-7 fonti `JS_ONLY`/`403`. Valutazione nel TASK SOURCE_EXPANSION_02.
- **Non rifare** l'audit runtime né l'audit fonti: `docs/GITHUB_PIPELINE_RUNTIME_AUDIT.md` e
  `docs/SOURCE_EXPANSION_AUDIT_01.csv` sono validi.

---

## ORDINE

1. Leggere l'esito del run `33355679965`.
2. **TASK F** — completare il fix incrementale (A2). Sblocca tutto il resto.
3. **TASK G** — ritarare i segnali sul golden. È il difetto più grave del prodotto.
4. **TASK H** — riaccendere il cron, con orari confermati dall'utente.
5. **TASK I** — le 13 fonti pronte, separatamente da F.
6. **TASK L** — l'analisi, solo dopo G.

## CONSEGNA

- Un commit per task, messaggi in inglese.
- Report finale con numeri prima/dopo per F (fonti che saltano il supplemento, `duration_sec`,
  `items_written`) e per G (quanti componenti cambiano su due run, quanti valori di
  `classification`).
- Se un task risulta già fatto, dirlo e saltarlo — non inventare lavoro.
