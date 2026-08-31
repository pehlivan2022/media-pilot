# TASK — FASE 2, completamento

**Repo:** `C:\Users\frontofficedx\Desktop\media-pilot` (branch `master`)
**Scritto:** 2026-08-31, da una sessione esterna che ha verificato lo stato live via `gh`
**Prerequisito:** leggere tutto prima di eseguire. Il punto 0 va fatto per primo.

---

## 0. PRIMA DI TUTTO

```bash
git add docs/TASK_FASE2_COMPLETAMENTO.md && git commit -m "Add FASE 2 completion task"
```

Questo file è untracked. Il 31/08 alle 00:14 un `git clean -fdx` in questo repo ha cancellato
in modo irreversibile tutti i file non tracciati e ignorati, incluso un task doc mai committato.
**Non eseguire mai `git clean -fdx` qui**: `.gitignore` contiene `data/*` e il flag `-x` include
gli ignorati; `git clean` fa `unlink` diretto, non passa dal Cestino, non è recuperabile.

---

## 1. STATO VERIFICATO (misurato, non dedotto)

Il test a 2 run è **concluso**. Entrambi verdi, ma il criterio di accettazione non è passato.

```
Daily Pipeline  run 1  33340817668  success  49m52s
Daily Pipeline  run 2  33343055346  success  54m59s   <- più lento del primo
Publish Pages   x2     workflow_run  success  32s / 33s
```

| commit su master | `new_items_this_run` | `duration_sec` |
|---|---|---|
| Actions run 1 | 1749 | 2967.7 |
| Actions run 2 | 1799 | 3271.7 |

**La persistenza `runtime-state` funziona.** Righe realmente scritte:

```
data/raw/2026-08-30.jsonl   1811 righe   (65,9 MB)   <- run 1
data/raw/2026-08-31.jsonl     60 righe   (238 KB)    <- run 2
```

Il dedup ha scartato 1751 item su 1811. Quindi lo stato passa correttamente da un run all'altro.

**`new_items_this_run` è una metrica fuorviante**: in `pilot/run_all.py:145` vale
`len(s["raw_items"])`, cioè gli item **scaricati**, non quelli **scritti**. Per questo il run 2
sembra aver raccolto 1799 item nuovi quando ne ha scritti 60.

---

## 2. CAUSA DEI 55 MINUTI — isolata

**Non** è `BACKFILL_DAYS_DEFAULT = 30`. `run_monitor.py:62-68` calcola
`days = max(history_days)` dai target selezionati, e `config/monitoring.yaml:141` per
`pilot_daily_all` dichiara `history_days: 7`. La finestra è già 7 giorni.

La causa è in `pilot/collect.py:446-450`:

```python
if is_rss and supplement_history:
    sup_items, sup_errors = collect_supplemental_history(source, window_start)
```

`collect_supplemental_history()` viene chiamata per **ogni fonte RSS a ogni run**, senza
ricevere gli URL già presenti in `data/raw/`. Rifà quindi fino a `MAX_BACKFILL_URLS = 100`
fetch di pagine per fonte (sitemap o Wayback CDX), ogni volta, e il dedup li scarta solo
**in scrittura** (`collect.py:462-472`), cioè dopo che sono già stati scaricati e passati a
trafilatura.

25 fonti RSS × fino a 100 fetch × (richiesta + retry + estrazione) = i ~50 minuti.

**Nota importante**: `collect_from_sitemap_backfill()` accetta già un parametro
`exclude_canonical` (`collect.py:147`) progettato esattamente per saltare ciò che è già noto.
Non viene semplicemente popolato dallo storico raw.

Effetto collaterale peggiore del tempo: **2 crawl completi al giorno su 33 testate**, che
rifanno sempre le stesse ~100 URL per fonte. È il modo più rapido per farsi bloccare (le fonti
con `403` sono già 3-4, vedi `docs/SOURCE_EXPANSION_AUDIT_01.csv`).

---

## TASK A — Non riscaricare ciò che è già in `data/raw/` (priorità 1)

**Obiettivo:** run incrementale in minuti, non in ~55.

Due strade, scegliere la più piccola che regge:

**A1 (preferita).** Saltare del tutto il supplemento per le fonti che hanno già storia
sufficiente. `config/sources.yaml` contiene già `window_actual_days` per fonte, calcolato e
riscritto a ogni run da `compute_window_actual_days()` (`collect.py:478-480`). Condizione:

```python
if is_rss and supplement_history and source.get("window_actual_days", 0) < days:
    sup_items, sup_errors = collect_supplemental_history(source, window_start)
```

**A2.** Popolare `exclude_canonical` con i `final_url`/`raw_id` già presenti in `data/raw/*.jsonl`
e passarlo lungo la catena `collect_supplemental_history` → `collect_from_sitemap_backfill`.
Più invasiva, ma non perde URL nuovi vecchi di qualche giorno.

**Criteri di accettazione:**
- Un run locale con storia già presente scende sotto i 10 minuti (misurare `duration_sec` in
  `data/pipeline_health.json` prima e dopo).
- Il numero di righe scritte in `data/raw/<oggi>.jsonl` **non cala** rispetto a un run senza la
  modifica: verifica su una fonte campione che nessun articolo nuovo venga perso.
- `python -m pilot.test_pipeline` → 25/25 (richiede `data/golden/` e `data/fixtures/`, vedi TASK C).
- Un run su Actions dopo il fix scende sotto i 10 minuti.

---

## TASK B — Il cron è vivo e non validato (priorità 1, scade alle 07:00)

`.github/workflows/daily-pipeline.yml:8-9`:

```yaml
- cron: '0 5 * * *'
- cron: '0 11 * * *'
```

Attivo su `master`, cioè ~07:00 e ~13:00 Europe/Sarajevo. Parte da solo **anche se il TASK A
non è stato fatto**, rifacendo due crawl completi al giorno.

**Decisione richiesta all'utente** (non decidere da solo):
- **(a)** commentare il blocco `schedule:` finché il TASK A non è verificato su Actions, oppure
- **(b)** lasciarlo attivo accettando 2× ~55 min/giorno di crawl finché il fix non arriva.

Se il TASK A viene completato prima delle 07:00, la domanda decade: fare A, poi lasciare il cron.

Verificare anche con l'utente gli orari esatti: il cron GitHub è UTC fisso e **non segue l'ora
legale**, quindi in inverno slitta a 06:00/12:00 locali. È un default scelto, non un requisito
confermato.

---

## TASK C — `golden/` e `fixtures/` esistono solo su questo disco (priorità 2)

`data/golden/` (9 file, incluso `golden_dataset.json` e le annotazioni a/b) e `data/fixtures/`
(3 file) sono stati recuperati il 31/08 da un vecchio zip e ricopiati a mano. Sono sotto
`data/*` nel `.gitignore`, quindi:

- non sono su GitHub,
- non esistono su un runner Actions,
- spariscono al prossimo `clean`, o semplicemente su un'altra macchina.

Sono **dati curati a mano, non rigenerabili** — le annotazioni golden sono l'unica base di
valutazione della qualità del clustering/scoring.

**Fare:** aggiungere in `.gitignore` le eccezioni, sul modello di quella già presente per
`pipeline_health.json`:

```
data/*
!data/pipeline_health.json
!data/golden/
!data/fixtures/
```

poi `git add -f data/golden data/fixtures` e committare. Sono ~700 KB in totale, verificare.
Se l'utente preferisce non metterli nel repo pubblico, l'alternativa è un artifact o un branch
separato — ma **non lasciarli solo su disco locale**.

Copia di sicurezza attuale: `C:\Users\frontofficedx\Desktop\media-pilot-RECUPERO-2026-08-31\data\`.

---

## TASK D — Rendere onesta la metrica (priorità 3, banale)

`pilot/run_all.py:145` scrive `new_items_this_run: len(s["raw_items"])` = item **scaricati**.
`collect()` conosce già il numero di item realmente **scritti** (variabile `written`,
`collect.py:466-471`) ma non lo restituisce.

Far tornare a `run_all` anche `written` e scrivere in `pipeline_health.json` entrambi:
`items_fetched` e `items_written`. Senza questo, ogni futura diagnosi di "il run è lento /
non incrementale" riparte dallo stesso equivoco che ha fatto fallire la lettura del test a 2 run.

---

## TASK E — Analisi dei risultati (priorità 2, mai iniziata)

È l'ultima cosa che l'utente aveva chiesto ("using pipeline to analise the results") e non è
stata toccata. **Non è ancora specificata**: prima di scrivere codice, produrre una proposta di
1 pagina e farla approvare.

Punto di partenza obbligato — c'è un problema noto e non risolto sui segnali:

> Su 5 segnali calcolati, 4 non variano mai fra un run e l'altro (sono di fatto inerti), e
> `velocity` ha un bug di unità che **peggiora** man mano che il corpus cresce.

**Verificare questa affermazione prima di costruirci sopra**: leggere `pilot/signals.py` e
confrontare `assets/data/signals.json` fra due commit consecutivi di `master` (i due run Actions
sono ideali: `261dfdf` e `1c63702`). Se i valori sono identici a corpus diverso, il segnale è
inerte e va sistemato **prima** di qualsiasi analisi che ci si appoggi.

Solo dopo: definire cosa significa "analizzare i risultati" (trend per entità? anomalie per
fonte? confronto fra testate sullo stesso evento?) e proporlo.

---

## FUORI SCOPO — non fare

- **Non scrivere scraper per Facebook/Instagram.** Delle 110 fonti candidate, 108 hanno un
  `website_url` e **zero** sono raggiungibili solo via social. Non c'è RSS, le pagine pubbliche
  sono dietro login-wall, e scrapparle con un account loggato viola i ToS. La via legittima è la
  Meta Content Library (sostituta di CrowdTangle, chiuso il 14/08/2024): richiesta separata.
- **Non aggiungere fonti nuove in questo task.** C'è un task dedicato:
  `..\media-pilot-RECUPERO-2026-08-31\TASK_SOURCE_EXPANSION_02.md` (13 fonti già validate e mai
  abilitate). Non mescolare le due cose: qui si stabilizza la pipeline, lì la si allarga.
- **Non aggiungere Scrapling / Playwright.** Valutazione separata nel task sopra, e va decisa su
  un numero misurato di articoli/settimana, non a intuito.
- **Non rifare l'audit runtime**: `docs/GITHUB_PIPELINE_RUNTIME_AUDIT.md` è valido.

---

## ORDINE DI ESECUZIONE

1. **TASK 0** — committa questo file.
2. **TASK A** — il fix incrementale. È il collo di bottiglia di tutto il resto.
3. **TASK B** — chiedi all'utente del cron (o decade, se A è pronto prima delle 07:00).
4. **TASK C** — metti al sicuro `golden/` e `fixtures/`.
5. **TASK D** — metrica onesta.
6. **TASK E** — proposta di analisi, approvazione, poi implementazione.

## CONSEGNA

- Un commit per task, messaggi in inglese come gli esistenti.
- Report finale con: `duration_sec` e righe scritte **prima e dopo** il TASK A, su un run locale
  e su un run Actions; esito di `python -m pilot.test_pipeline`; e la decisione presa sul cron.
- Se un task risulta già fatto o non necessario, dillo e salta — non inventare lavoro.
