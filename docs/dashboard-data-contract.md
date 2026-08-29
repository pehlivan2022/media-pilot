# Dashboard data contract

§21, `MEDIA_PILOT_FINAL_HANDOFF.md`. Un file per ognuno degli 8 JSON in `assets/data/`, scritto
PRIMA di qualunque API (§22: JSON statici prima, API dopo). Copre solo i tre file che questo giro
di lavoro ha reso reali (`rassegna.json`, `trending.json`, `signals.json`); gli altri cinque
restano demo, dichiarato sotto — non descriverne lo schema come se fosse stabile.

---

## `assets/data/rassegna.json`

**schema_version**: non versionato esplicitamente (nessun campo `schema_version` nel file). Un
array di oggetti articolo.

**Scritto da**: `pilot/export_dashboard.py:export_rassegna()`, dentro `pilot.run_all`.

**required** (sempre presenti, mai `null` per costruzione): `id`, `title`, `modules` (array,
puo' essere vuoto), `date`, `url`.

**optional** (possono essere `null`): `signal_score`, `cluster_size`, `menu`, `territory`,
`territory_ij` (**sempre `null` oggi**, §26 — mai dedotto), `summary`, `source_note`,
`verification`, `provenance`, `origin_type`, `n_copies`, `cluster_id`.

**Layer 3 / giudizio** (`risk`, `opportunity`, `wedge`, `owner`, `deadline`,
`signal_to_vrh`, `signal_to_media`, `suggested_responses`, `user_info`): SEMPRE ai default
(0/`null`/`false`/`[]`) — a cura umana, il pilot non li scrive mai (`_JUDGMENT_DEFAULTS`).

**enum**: `menu` ∈ {`news`,`social`,`local`,`institutions`,`campaign`,`null`}. `verification` ∈
{`OFFICIAL_CONFIRMED`,`MULTI_SOURCE`,`SINGLE_SOURCE`}. `provenance` ∈ {`OFFICIAL`,`MANUAL`,`MEDIA`}.
`origin_type` ∈ {`agency_repost`,`original_reporting`}.

**date format**: ISO 8601 UTC, `Z` finale (es. `2026-08-27T19:07:57Z`).

**null policy**: dato non verificato = `null`, mai omesso ne' inventato.

**provenance (del dato, non del giudizio)**: ogni riga viene da un articolo raccolto e verificato
via `url`; `verification`/`provenance` (i due campi qui sopra) descrivono quanto e' confermato.

---

## `assets/data/trending.json`

**schema_version**: nessuno. Un array di oggetti **entita'**, non articolo — schema diverso da
rassegna.json di proposito (vedi `pilot/trending.py`, nota architetturale in cima al file: forzare
questi dati nello schema-articolo avrebbe richiesto inventare `title`/`menu`).

**Scritto da**: `pilot/trending.py:export_trending_json()`, dentro `pilot.run_all`. Solo le entita'
con `mentions_24h>0` o `mentions_4h>0` (le altre restano in `data/trending_entities.jsonl`, non
qui — stessa logica del filtro `is_relevant` su rassegna.json).

**required**: `entity_id` (chiave REALE di `config/entities.yaml`, mai inventata), `label`,
`mentions_24h` (int), `unique_events_24h` (int), `unique_sources_24h` (int), `top_events` (array,
puo' essere vuoto), `evidence` (array di URL reali, puo' essere vuoto).

**optional** (`null` se la finestra storica non basta, MAI stimato): `baseline_7d` (media
GIORNALIERA di mention sugli ultimi 7gg, non oraria — vedi nota sotto), `momentum`
(`(mentions_24h - baseline_7d) / baseline_7d`, `null` se `baseline_7d` e' `null` o 0),
`last_event_at`.

**ATTENZIONE nome doppio**: `data/trending_entities.jsonl` (file interno, non questo) usa
`baseline_7d` per un concetto DIVERSO (mediana di mention per bucket da 4h, usata per
`acceleration`). Il `baseline_7d` DENTRO `trending.json` e' invece `baseline_daily_7d` nel file
interno (media per GIORNO). Stesso nome, scala diversa, per restare fedeli al campo letterale
richiesto da `MEDIA_PILOT_FINAL_HANDOFF.md` §15 — non unificare i due senza aggiornare entrambi i
consumer.

**top_events[]**: `{cluster_id, title, url, source_id, published_at, n_items}` — tutti reali.

**date format**: ISO 8601 UTC.

**null policy**: `baseline_7d`/`momentum`/`last_event_at` `null` quando non misurabili. Mai un
`0` finto al posto di `null`.

---

## `assets/data/signals.json`

**schema_version**: nessuno. Un array di **SignalCandidate**, SOLO quelli con
`classification: "REVIEW"` (i `MONITORING` restano in `data/signal_candidates.jsonl`, non qui).

**Scritto da**: `pilot/signals.py:export_signals_json()`, dentro `pilot.run_all`.

**required**: `entity_id`, `label`, `classification` (sempre `"REVIEW"` in questo file, per
costruzione — vedi sopra), `why_now` (stringa template su numeri reali, MAI testo generato da un
LLM), `entities` (array), `events` (array di `cluster_id`), `metrics` (oggetto, vedi sotto),
`sources` (array di `source_id`), `evidence` (array di URL), `confidence` (float 0-1, vedi nota),
`confidence_components` (oggetto booleano, quali soglie hanno acceso il segnale), `provenance`
(sempre `"PILOT_RULES"` — nessun testo/giudizio da modello).

**optional** (`null` se non determinabile): `first_seen`, `last_seen`.

**metrics{}**: `mentions_24h`, `unique_events_24h`, `unique_sources_24h`, `momentum`,
`acceleration`, `max_entity_salience`, `max_co_entities_in_event` — tutti numeri reali dal
Trending Engine, nessuno ricalcolato qui.

**NOTA su `confidence`**: e' un CONTEGGIO di segnali misurati su 5 (`confidence_components`),
`round(n_veri / 5, 3)` — non una probabilita' stimata, non calibrata su un golden set di Signal
confermati/respinti da un umano (non esiste ancora). Trattarlo come un indice di quante regole
hanno acceso, non come "quanto e' probabile che sia vero".

**date format**: ISO 8601 UTC.

**null policy**: `first_seen`/`last_seen` `null` se non ricostruibili da `top_events`.

---

## File NON toccati in questo giro — restano demo, schema non descritto qui

`assets/data/alerts.json`, `cases.json`, `tasks.json`, `archive.json`, `candidates.json`,
`candidates_source.json`: contenuto demo/scenario (v19-large-light), generato da
`tools/build-data.js` + `radar.js` sul dataset di esempio, non dalla pipeline del pilot.
Descriverne uno schema "contrattuale" ora sarebbe prematuro — dipendono da Alert/Case/workflow
umano (§18-20 dell'handoff), non ancora costruiti. Non generare questi file dal pilot finche' quel
lavoro non e' fatto: mescolerebbe dati demo e dati reali senza marcarli (§38, vietato).
