# SOURCE_EXPANSION_AUDIT_01 — v14 vs config/sources.yaml

Dati completi riga-per-riga: `docs/SOURCE_EXPANSION_AUDIT_01.csv` (110 righe, tutte le fonti
`01_MASTER_ALL` di `media_pilot_fonti_facebook_aggiornate_v14.xlsx`). Problemi/errori tecnici
per fonte: `docs/SOURCE_PROBLEMS_01.csv`. Script usato: `pilot/source_audit_v14.py` (non tocca
`config/sources.yaml` direttamente — scrive solo l'audit; l'aggiunta a `sources.yaml` è stata
fatta a mano dopo revisione).

## Input

- 110 righe in `01_MASTER_ALL`, 108 con `website_url`, 2 senza (solo social/persona:
  `BL_IJ3_012` Draško Stanivuković, `POL_RS_012` Pokret za državu).
- `status_tag`: 100 VERIFICATA, 9 MANCANTE, 1 DA_VERIFICARE.
- `priority_tier`: 25 tier 1, 47 tier 2, 38 tier 3.

## Current (prima di questo task)

18 fonti attive in `config/sources.yaml`.

## Diff (per canonical domain, poi source_id)

- **Già attive**: 18/110 (match per dominio canonico).
- **Candidate non attive con website_url**: 90.
- **Senza website_url**: 2 (`NOT_USEFUL`, nessuna azione).
- **ID conflict** (source_id v14 coincide con un id attivo su un dominio diverso): **0** — nessun
  conflitto trovato.
- **Duplicato di persona/partito sotto due domini diversi**: `POL_RS_010` "Za pravdu i red"
  (`pravdared.com`) vs `PART_RS_ZPIR_001` "Za pravdu i red" (`zapravduired.org`, l'unica riga
  davvero nuova aggiunta dalla v14 rispetto alla v12). Testati entrambi: `pravdared.com` →
  `DEAD_DOMAIN`, `zapravduired.org` → `NO_ARTICLE_LINKS`. Nessuno dei due è READY, quindi nessun
  doppione promosso — annotato per revisione futura se uno dei due domini torna online.

## Tests

**Ordine seguito**: Tier 1 gap (6 candidati, tutti i 25 tier-1 meno i 19 già attivi meno 2 senza
url... vedi nota sotto) → Tier 2 mirato (45 candidati, filtrati per le categorie del §7: Doboj/IJ5,
Ujedinjena Srpska, partiti RS, istituzioni elettorali, media RS locali, economia/investigativo,
BiH monitoring) → Tier 3 **non testato** (nessun gap geografico/tematico residuo dopo tier 1+2,
budget di fetch non speso per policy §8/§15). Un candidato tier 2 (`FBIH_005` Faktor.ba) non
rientrava in nessuna delle categorie mirate ed è stato lasciato NOT_TESTED come i tier 3.

**Nota sul Tier 1**: dei 25 candidati tier-1 in v14, 18 erano già attivi (esattamente le 18 fonti
del progetto) e 1 senza `website_url` (`BL_IJ3_012`) → 18 + 1 = 19, restano **6** davvero da
testare (25 − 19 = 6, la lista di questo paragrafo). La lista dei "24 siti web" del task §6 non
includeva `BL_IJ3_012` (aggiunto dopo, senza url) — coerente. L'altra riga senza url
(`POL_RS_012`) è tier 2, non tier 1.

**Distribuzione `test_status` sulle 110 righe** (51 testate dal vivo, 18 già attive, 2 senza url,
39 non testate per policy): (1 fetch homepage + RSS discovery leggero + sitemap/robots +
fallback link-homepage per candidato — mai backfill storico completo su un candidato non ancora
promosso):

| test_status | conteggio |
|---|---:|
| READY_RSS | 19 |
| READY_HTML (solo homepage-link, vedi nota) | 6 |
| READY_SITEMAP | 3 |
| NO_RSS | 9 |
| NO_ARTICLE_LINKS | 6 |
| JS_ONLY | 4 |
| DEAD_DOMAIN | 3 |
| BLOCKED_403 | 1 |
| ROBOTS_RESTRICTED | 0 |
| ALREADY_ACTIVE | 18 |
| NOT_USEFUL (no url) | 2 |
| NOT_TESTED (tier 3 + 1 fuori categoria) | 39 |

**Nota tecnica importante sui 6 `READY_HTML`**: la fonte estrae articoli validi seguendo i link
della homepage, ma **`pilot/collect.py::collect_from_html_source` raccoglie solo se il campo
`method` contiene `sitemap` o `wayback`** (righe 330-342) — un metodo `html_home_links` puro
ritorna sempre 0 item con `MANUAL_ONLY`. Prova dal vivo di questo comportamento sulla fonte già
attiva `RS_IJ_018` (InfoBijeljina, `method: html_home_links`): 0 item raccolti nel run
`pilot_daily_all` del 2026-08-29, vedi `SOURCE_PROBLEMS_01.csv` (`REGRESSION_EXISTING_SOURCE`).
Per questo, **i 6 candidati READY_HTML non sono stati promossi** in questo task, anche se
tecnicamente "pronti": promuoverli avrebbe prodotto righe morte in `sources.yaml`. Restano
`READY_NOT_ENABLED_YET` in decisione, con nota esplicita.

## Added (15 fonti promosse, tetto MAX 15 del §15)

Selezionate tra i 22 candidati `READY_RSS`/`READY_SITEMAP` (unici metodi davvero raccoglibili da
`pilot/collect.py`) per: 1) Doboj/IJ5, 2) rilevanza elettorale US/RS, 3) importanza istituzionale,
4) copertura incrementale per IJ (IJ1/IJ2/IJ7/IJ8/IJ9 non coperte da nessuna fonte attiva prima di
questo task), 5) affidabilità tecnica — non per volume puro (§20).

| source_id | name | domain | method | recent items | decision |
|---|---|---|---:|---:|---|
| RS_IJ_015 | Granice Doboja | granicedoboja.info | rss | 6 | PROMOTED — Doboj/IJ5 |
| BIH_ELEC_005 | Istinomjer | istinomjer.ba | sitemap | 2 | PROMOTED — fact-check elettorale, election_relevance 0.80 (max) |
| SRC_001 | Detektor / BIRN BiH | detektor.ba | rss | 10 | PROMOTED — investigativo/istituzionale |
| BL_IJ3_005 | Buka | 6yka.com | rss | 10 | PROMOTED — IJ3, testata critica/urbana |
| BL_IJ3_004 | Frontal.ba | frontal.ba | rss | 10 | PROMOTED — IJ3, commento politico |
| ECO_002 | Akta.ba | akta.ba | sitemap | 6 | PROMOTED — economia/istituzionale |
| FBIH_003 | Oslobođenje | oslobodjenje.ba | rss | 50 | PROMOTED — copre FBiH, alto volume |
| RS_IJ_002 | InfoPrijedor | infoprijedor.ba | rss | 10 | PROMOTED — IJ1, nuova copertura geografica |
| RS_IJ_005 | Micro Mreža | micromreza.com | rss | 10 | PROMOTED — IJ2, nuova copertura geografica |
| RS_IJ_021 | Zvornički.ba | zvornicki.ba | rss | 10 | PROMOTED — IJ7, nuova copertura geografica |
| RS_IJ_027 | Spin Info | spin-portal.info | rss | 5 | PROMOTED — IJ8, nuova copertura geografica |
| RS_IJ_030 | Direkt Portal | direkt-portal.com | rss | 10 | PROMOTED — IJ9, nuova copertura geografica |
| RS_IJ_009 | Derventski List | derventskilist.net | rss | 10 | PROMOTED — IJ4, rinforza area Doboj |
| FBIH_002 | Dnevni avaz | avaz.ba | rss | 10 | PROMOTED — quotidiano FBiH-wide |
| BL_IJ3_008 | Banjaluka.net | banjaluka.net | rss | 10 | PROMOTED — IJ3, capitale RS |

Restano `READY_NOT_ENABLED_YET` (cap raggiunto, vedi CSV per dettaglio): `BL_IJ3_009`,
`RS_IJ_003`, `RS_IJ_008`, `RS_IJ_022`, `RS_IJ_026`, `FBIH_004`, `SRC_010`.

## Problems

Vedi `docs/SOURCE_PROBLEMS_01.csv` per il dettaglio (26 righe). Sintesi per `problem_code`:

| problem_code | conteggio | note |
|---|---:|---|
| NO_RSS | 9 | feed assente o vuoto negli ultimi 7g |
| NO_ARTICLE_LINKS | 6 | homepage raggiungibile, nessun link-articolo recente estraibile |
| JS_ONLY | 4 | probabile SPA, nessun testo senza JS — nessun browser automation introdotto (§10) |
| DEAD_DOMAIN | 3 | dominio non raggiungibile (incl. `pravdared.com`) |
| BLOCKED_403 | 1 | `zurnal.info` |
| NO_WEBSITE_URL | 2 | solo social/persona in v14 |
| REGRESSION_EXISTING_SOURCE | 1 | `RS_IJ_018`, preesistente, non causata da questo task |

Nessun `ROBOTS_RESTRICTED`, `BLOCKED_429`, `TIMEOUT`, `SSL_ERROR` incontrato nei 51 test live.

## Before / After (run pipeline reale, 2026-08-29)

| metrica | prima (18 fonti) | dopo (33 fonti) |
|---|---:|---:|
| fonti attive | 18 | 33 |
| clean | 2.267 | 3.623 |
| dedup | 1.947 | 2.957 |
| cluster | 462 | 613 |
| rassegna (rilevanti) | 683 | 1.065 |
| entità attive (24h) | 24 | 26 |
| signal REVIEW | 17 | 20 |
| runtime pipeline | 251,6s | 2685,3s (~44,8 min) |

Le 14 fonti in `sources_failed` del run (vedi `pipeline_health.json`) hanno tutte raccolto item
regolarmente nel metodo primario — l'errore è quasi sempre nel **supplemento storico
best-effort** (sitemap/Wayback CDX oltre l'orizzonte del feed RSS, §B1 di `collect.py`), non nel
metodo che le rende READY. Verificato riga per riga in `data/errors.jsonl`: soprattutto timeout
sulla Wayback CDX API (`web.archive.org/cdx/search/cdx`, nota già presente nel codice come
instabile su query strette) e pagine `OUT_OF_WINDOW`/`EMPTY_CONTENT` normali di pulizia.

## Per-fonte (§19/§20) — fetched/valid/dedup/relevant e valore incrementale

Misurato sul run reale del 2026-08-29 (`data/clean.jsonl`, `data/items.jsonl` per `source_id`/
`source_ids`, non per volume puro — §20). `dup_rate` = quota di `valid` che NON sopravvive al
dedup (finita in un gruppo duplicato rappresentato da un'altra fonte).

| source_id | name | fetched | valid | survived_dedup | relevant | dup_rate | incremental_value |
|---|---|---:|---:|---:|---:|---:|---|
| RS_IJ_015 | Granice Doboja | 6 | 6 | 6 | 3 | 0% | **HIGH** — unica fonte hyperlocal Doboj/IJ5 aggiunta |
| BIH_ELEC_005 | Istinomjer | 100 | 100 | 97 | 96 | 3% | **HIGH** — 96/100 rilevanti, fact-check elettorale mai coperto |
| SRC_001 | Detektor / BIRN BiH | 10 | 10 | 10 | 1 | 0% | MEDIUM — copertura istituzionale/investigativa strategica, resa attuale bassa (1 rilevante) |
| BL_IJ3_005 | Buka | 110 | 110 | 71 | 24 | 35% | **HIGH** — voce critica/urbana IJ3, 24 rilevanti |
| BL_IJ3_004 | Frontal.ba | 44 | 44 | 42 | 23 | 5% | **HIGH** — commento politico IJ3, 23 rilevanti |
| ECO_002 | Akta.ba | 99 | 99 | 98 | 21 | 1% | MEDIUM — economia/istituzionale, 21 rilevanti |
| FBIH_003 | Oslobođenje | 50 | 50 | 50 | 6 | 0% | **LOW** — alto volume ma solo 6/50 rilevanti (12%), news FBiH generaliste |
| RS_IJ_002 | InfoPrijedor | 13 | 10 | 10 | 1 | 0% | MEDIUM — nuova copertura IJ1, volume basso |
| RS_IJ_005 | Micro Mreža | 100 | 100 | 98 | 19 | 2% | MEDIUM — nuova copertura IJ2 |
| RS_IJ_021 | Zvornički.ba | 100 | 100 | 97 | 16 | 3% | MEDIUM — nuova copertura IJ7 |
| RS_IJ_027 | Spin Info | 21 | 21 | 21 | 18 | 0% | **HIGH** — nuova copertura IJ8 + 18/21 rilevanti (86%) |
| RS_IJ_030 | Direkt Portal | 10 | 10 | 10 | 7 | 0% | MEDIUM — nuova copertura IJ9 |
| RS_IJ_009 | Derventski List | 51 | 50 | 49 | 18 | 2% | MEDIUM — IJ4, rinforza area Doboj |
| FBIH_002 | Dnevni avaz | 110 | 109 | 14 | 1 | 87% | **LOW** — 87% duplicato con corpus esistente, solo 1 rilevante sopravvissuto |
| BL_IJ3_008 | Banjaluka.net | 110 | 110 | 108 | 41 | 2% | **HIGH** — 41 rilevanti, copertura capitale RS |

Nota onesta: due testate nazionali di grande volume (`FBIH_003` Oslobođenje, `FBIH_002` Dnevni
avaz) hanno reso **LOW** per valore incrementale nonostante fossero le fonti con più item
raccolti — esattamente il caso che il §20 chiede di non confondere con "volume puro". Restano
promosse in questo giro (erano le uniche READY_RSS a copertura FBiH-wide oltre a Klix.ba già
attivo) ma sono le prime candidate a una revisione se il tetto di 15 dovesse liberarsi.

## Daily mode

- `pilot_daily_all` creato in `config/monitoring.yaml`: **sì**.
- `runs_per_day: 1`, `history_days: 7` (recent-only per le fonti nuove, §18).
- Target esistenti (`us_core`, `doboj`, `institutions`, `opposition_competitors`, `background`)
  **invariati**.
- Comando esatto: `python -m pilot.run_monitor --target pilot_daily_all`
- Run reale eseguita il 2026-08-29, exit 0, vedi tabella Before/After sopra.
