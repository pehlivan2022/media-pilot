# GitHub Pages Deploy — Audit (FASE 1)

Data: 2026-08-30. Verificato dal vivo su `C:\Users\frontofficedx\Desktop\media-pilot`.

## 0. Stato repository

- **Nessuna cartella `.git`** — confermato, il repo non esiste ancora.
- `git` 2.55.0, `gh` 2.96.0 — installati e funzionanti.
- `gh auth status`: autenticato come `pehlivan2022`, scopes `gist, read:org, repo, workflow`. Nessun blocco qui.
- `gh api user` non restituisce il campo `plan` con lo scope corrente (endpoint pubblico limitato) — non verificabile via API. **Da confermare a voce**: piano Free o a pagamento (Pro/Team)? Questo decide se un repo privato può avere Pages.

## 1. `.gitignore` — dimensioni misurate

| File | Dimensione | Note |
|---|---|---|
| `data/clean.jsonl` | 132 MB (138 104 476 B) | oltre il limite 100 MB di GitHub |
| `data/scored_items.jsonl` | 18.4 MB | |
| `data/items.jsonl` | 17.8 MB | |
| `data/pipeline_health.json` | 593 B | **unica eccezione**, alimenta la card di stato |

`.gitignore` attuale copre solo `.env`, `__pycache__/`, `*.pyc`, `data/raw/`, `data/corpus.db`, `*.zip` — non copre `data/*.jsonl`. Confermato: senza fix il push fallirebbe su `clean.jsonl` (>100MB).

Repo escludendo `data/`: **3.4 MB** (misurato con `du -sh --exclude=data .`), coerente con la stima di ~4 MB del task.

Altri file grossi in root non coperti da `.gitignore` che vanno esclusi dal repo/da Pages: `media-pilot-dashboard.zip` (404 KB, già coperto da `*.zip`), `embedded-data.js` (584 KB, va incluso nel repo ma è candidato all'esclusione da Pages, vedi §4).

## 2. Dashboard statica — pagine HTML

11 pagine reali confermate in root: `index.html`, `us.html`, `vrh.html`, `media.html`, `case.html`, `eksperti.html`, `konkurenti.html`, `ostali.html`, `arhiva.html`, `go.html`, `simulator.html`.

Da **escludere** da Pages: `_selftest.html`, `_selftest_beta.html` (root), più `data/rassegna_preview.html`, `data/trending_signals_preview.html`, `data/fixtures/dobojski_home.html`, `pilot/golden/review.html` (fuori da `data/pipeline_health.json` e dalla dashboard vera e propria, non vanno mai pubblicati).

## 3. JS — shell e pagina

Shell/condivisi (9): `dashboard-config.js`, `store.js`, `radar.js`, `data.js`, `ui.js`, `header.js`, `pwa.js`, `sw.js`, `embedded-data.js`.

Di pagina (10, uno per pagina tranne `index`→`page-home.js`): `page-home.js`, `page-us.js`, `page-vrh.js`, `page-media.js`, `page-case.js`, `page-eksperti.js`, `page-konkurenti.js`, `page-ostali.js`, `page-arhiva.js`, `page-go.js`, `page-simulator.js`.

`embedded-data.js` (584 KB) è referenziato in tutte le 11 pagine reali (più i selftest) — è il fallback per apertura da `file://`. Su Pages il `fetch` di `assets/data/*.json` funziona in HTTPS, quindi **è un candidato all'esclusione**; se lo si esclude, la FASE 5 (test) deve verificare che tutte le pagine si aprano comunque, altrimenti va rimesso — così come chiesto dal task.

`tools/build-data.js` è uno script di build offline, non fa parte della dashboard pubblicata: resta fuori da `_site/`.

## 4. Dati — `assets/data/`

Confermati 9 JSON letti dalla dashboard (esclusa `rassegna.json.demo-backup`, che non va pubblicato):

- **Reali, cambiano ad ogni run**: `rassegna.json`, `trending.json`, `signals.json`
- **Demo, ferme al 26 agosto**: `alerts.json`, `archive.json`, `candidates.json`, `cases.json`, `tasks.json`

Più `data/pipeline_health.json` (593 B) fuori da `assets/data/`, anch'esso reale e aggiornato ad ogni run — quarto file reale come da task.

`assets/data/` pesa ~1.9 MB in totale (confermato).

**Discrepanza trovata, non nel task originale**: esiste anche `assets/data/candidates_source.json`, referenziato solo da `tools/build-data.js` e da doc interni — è un input di build per generare `candidates.json`, **non è letto da nessuna pagina/JS della dashboard**. Va escluso dalla pubblicazione su Pages (non serve al runtime).

## 5. Icone e PWA

`assets/icons/`: 3 file (`icon-192.png`, `icon-512.png`, `apple-touch-icon.png`) — confermati, nessun altro asset icona presente.

`manifest.webmanifest`, `sw.js`, `pwa.js` presenti in root, dimensioni minime (614 B, 1.4 KB, 619 B). Da verificare in FASE 3 che `start_url`/`scope` relativi reggano sotto `https://<utente>.github.io/<repo>/`.

## 6. Cosa NON va mai pubblicato

`pilot/`, `config/` (contiene `entities.yaml`, `sources.yaml`, `topics.yaml`, `scoring.yaml`, `pricing.yaml`, `monitoring.yaml` — 6 file YAML, tutti con logica di prodotto), `docs/` (39 file .md/.csv/.txt attuali, non 37 — il numero è leggermente cresciuto da quando è stato scritto il task, includendo questo stesso file di audit e il task stesso), `input/`, `tools/`, i `.bat` in root, `.env`, `data/` (tranne `pipeline_health.json`), `media-pilot-dashboard.zip`.

## 7. Sicurezza — verifica rapida

- `.env` contiene 3 righe che matchano `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY` (nomi delle chiavi, valori non ispezionati qui) — file già in `.gitignore`. Da confermare con `git check-ignore -v .env` **dopo** il primo `git init` (non eseguibile prima, il comando richiede un repo).
- Nessuna API key hardcoded trovata nei file HTML/JS letti finora.

## 8. Aperto — decisioni utente richieste prima di FASE 0.2

1. **Piano GitHub** (Free/Pro/Team) — non verificabile via API con lo scope attuale del token.
2. **Repo pubblico vs privato vs due repository** — vedi task §0.3, blocca tutto il resto.
3. **Nome del repository**.

Nessuna di queste tre è deducibile dal codice: come da istruzioni, mi fermo qui e non procedo a FASE 0.2 finché non le confermi.
