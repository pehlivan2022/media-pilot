# TASK — MEDIA PILOT: GitHub + GitHub Pages / FASE 1

Prompt per Claude Code. Si incolla intero. Progetto:

```
C:\Users\frontofficedx\Desktop\media-pilot
```

## RUOLO

Senior DevOps + GitHub Actions engineer. Lavori sul progetto Media Pilot **esistente**: non
riscrivere architettura né scraper, non toccare la pipeline. Prima audit, poi riuso, poi modifiche.
È un progetto **beta**: niente hardening esagerato, ma le API key non entrano nel repository.

## OBIETTIVO FASE 1

Mettere la **dashboard online su GitHub Pages**, con i dati JSON già prodotti dalla pipeline, e un
workflow manuale che la ripubblica quando glielo chiedo.

**Non** si esegue lo scraper da GitHub. **Non** si attiva nessuno scheduler. **Niente Aruba** in
questa fase. Il workflow parte solo con `workflow_dispatch`.

---

## FASE 0 — Il repository non esiste: crealo per primo

Verificato oggi: **non c'è nessuna cartella `.git`**. Tutto ciò che segue presuppone un repo che va
creato adesso.

### 0.1 — `.gitignore` PRIMA del primo commit (qui il lavoro fallisce se lo salti)

`.gitignore` attuale:

```
.env
__pycache__/
*.pyc
data/raw/
data/corpus.db
*.zip
```

**Non copre i file che fanno rifiutare il push.** Misurati:

- `data/clean.jsonl` → **132 MB** (GitHub blocca i file oltre 100 MB)
- `data/scored_items.jsonl` → 18 MB
- `data/items.jsonl` → 18 MB

Ignora tutta `data/` con **una sola eccezione**, perché `data/pipeline_health.json` alimenta la card
di stato della dashboard e deve stare nel repo:

```
data/*
!data/pipeline_health.json
```

Controlla con `git status --short` e `git count-objects -vH` prima di committare: senza `data/` il
progetto pesa **~4 MB**.

### 0.2 — Init, commit, repository, push

`git` 2.55 e `gh` 2.96 sono installati e funzionanti. Fai init, primo commit, crea il repository e
pusha. **Mostrami i comandi prima di eseguirli.** Se `gh auth status` dice che non sono
autenticato, fermati e dimmelo: l'autenticazione la faccio io.

### 0.3 — Pubblico o privato: decidilo con me, non da solo

Questo è il vero bivio della fase, perché **GitHub Pages pubblica un sito accessibile da chiunque
abbia l'URL**, indipendentemente dalla visibilità del repository. Verifica sul mio account (`gh api
user`, piano corrente) e presentami la situazione così:

- **Repo privato + Pages**: Pages da repository privato richiede un piano a pagamento (Pro/Team).
  Verifica se il mio piano lo consente. Il codice e `docs/` restano privati, ma il **sito
  pubblicato resta pubblico**.
- **Repo pubblico + Pages**: funziona su piano gratuito, ma diventa pubblico **tutto** ciò che è
  versionato — quindi anche `config/entities.yaml`, `config/sources.yaml` e i 37 file in `docs/`,
  che contengono la logica politica del progetto. Le API key no: `.env` è già in `.gitignore`.
- **Due repository**: il progetto privato, più un repo pubblico separato con solo i file statici
  della dashboard.

**Fermati e chiedimi quale voglio** prima di creare qualsiasi cosa. Non dare per scontato che vada
bene pubblicare `config/` e `docs/`.

In ogni caso aggiungi `<meta name="robots" content="noindex">` alle pagine pubblicate, così il sito
non finisce sui motori di ricerca.

---

## 1. AUDIT

Produci `docs/GITHUB_PAGES_DEPLOY_AUDIT.md`: cosa esiste, cosa viene pubblicato, cosa resta fuori,
problemi trovati.

Parti da questi fatti **già verificati** — confermali, non riscoprirli, e correggimi se sono
cambiati:

- Dashboard statica multipagina: **11 pagine HTML reali** (`index`, `us`, `vrh`, `media`, `case`,
  `eksperti`, `konkurenti`, `ostali`, `arhiva`, `go`, `simulator`), più `app.css`, i JS di shell e
  di pagina, `manifest.webmanifest`, `sw.js`, `pwa.js`, `assets/icons/`.
- **Dati letti dalla dashboard**: nove JSON in `assets/data/` più `data/pipeline_health.json`. Di
  questi solo **quattro sono reali e cambiano a ogni run**: `rassegna.json`, `trending.json`,
  `signals.json`, `pipeline_health.json`. Gli altri cinque (`alerts`, `archive`, `candidates`,
  `cases`, `tasks`) sono **ancora demo, fermi al 26 agosto**: vanno pubblicati perché la dashboard
  li legge, ma dichiarali come demo nell'audit.
- `assets/data/rassegna.json.demo-backup` **non va pubblicato**.
- `assets/data/` pesa ~1,9 MB in tutto.
- `embedded-data.js` (584 KB) è il fallback per l'apertura da `file://`. Su Pages il `fetch`
  funziona, quindi valuta se serve ancora online: se lo escludi, verifica che la dashboard
  funzioni comunque, e se non funziona rimettilo.

Non inventare path. Se un file che cerchi non c'è, scrivilo.

---

## 2. SICUREZZA (versione beta, essenziale)

- `.env` fuori dal repo — verifica con `git check-ignore -v .env`.
- Nessuna API key nei file versionati né nei log del workflow.
- Niente `data/raw`, `corpus.db`, `*.jsonl` grossi, `scheduler_run.log` nel repo.

Basta così. Non aggiungere scansioni di segreti, hook o policy: è una beta.

---

## 3. COSA VIENE PUBBLICATO SU PAGES

Pages deve servire **solo la dashboard**, mai `pilot/`, `config/`, `docs/`, `input/`, `tools/`, i
`.bat`, `.env`.

Non pubblicare la radice del repo. Il workflow costruisce una cartella `_site/` copiandoci dentro
**solo**:

```
*.html  (le 11 pagine reali, non _selftest*.html)
app.css
i .js di shell e di pagina
manifest.webmanifest, sw.js, pwa.js
assets/icons/**
assets/data/*.json   (escluso rassegna.json.demo-backup)
data/pipeline_health.json
.nojekyll
```

Struttura piatta identica a quella locale: `index.html` alla radice di `_site/`.

**Verifica prima di scrivere il workflow**: `manifest.webmanifest` usa `start_url: "index.html"` e
`scope: "."`, e `pwa.js` registra `sw.js` con path relativo — quindi il sito funziona anche sotto
`https://<utente>.github.io/<repo>/`. Se cambi qualcosa qui, ricontrolla che i path relativi
reggano sul sottopercorso.

Nota positiva: su Pages il sito è servito in **HTTPS**, quindi il service worker si registra
davvero e la PWA diventa installabile sul telefono — cosa che con l'apertura da `file://` era
impossibile.

---

## 4. WORKFLOW

Crea `.github/workflows/publish-pages.yml`, trigger **solo** `workflow_dispatch`.

Passi:

1. checkout;
2. costruisci `_site/` con l'elenco del punto 3;
3. valida ogni JSON copiato: sintatticamente corretto, non vuoto, non zero byte — se uno è rotto,
   **fallisci il workflow** invece di pubblicare dati corrotti;
4. genera `_site/assets/data/deploy-manifest.json`:

```json
{
  "generated_at": "...",
  "source": "github-actions",
  "status": "ok",
  "commit": "...",
  "files": [ { "name": "...", "size": 0, "sha256": "..." } ]
}
```

5. pubblica con le action ufficiali (`actions/configure-pages`, `actions/upload-pages-artifact`,
   `actions/deploy-pages`) e i permessi `pages: write` / `id-token: write`;
6. a deploy finito, **verifica dal vivo**: scarica dall'URL pubblicato `index.html` e i quattro JSON
   reali, controlla che rispondano 200 e che gli SHA256 coincidano con quelli del manifest.

Niente scraping, niente chiamate LLM, niente scheduler in questo workflow.

---

## 5. TEST

Lancia il workflow a mano (`gh workflow run`). **PASS solo se**: Action verde, sito raggiungibile,
le 11 pagine si aprono, i JSON rispondono 200, checksum coerenti, manifest presente, nessuna API
key nei log. Se fallisce, correggi e rilancia. Non dichiarare PASS con un punto scoperto.

Dammi l'URL finale e dimmi cosa devo guardare io sul telefono.

---

## 6. REPORT

`docs/GITHUB_PAGES_PHASE1_REPORT.md` con: checklist dei punti sopra, durata del workflow, peso del
sito pubblicato, URL, limiti incontrati, e cosa serve per la FASE 2.

---

## STOP

Quando la FASE 1 è PASS, **fermati**. Non implementare: scheduler/cron, esecuzione dello scraper su
Actions, chiamate Anthropic/DeepSeek, modifiche alla pipeline, deploy su Aruba, vector DB.

FASE 2 (dopo, non ora): esecuzione reale dello scraper su Actions, persistenza dello stato,
scheduler su fuso Europe/Sarajevo, e in seguito l'eventuale passaggio ad Aruba — per quello c'è già
`docs/TASK_GITHUB_ARUBA_FASE1.md`, da riprendere quando serve.

## Principi

Niente overengineering. Niente riscritture non necessarie. Niente supposizioni: prima verifichi,
poi modifichi. Ogni modifica reversibile.

**Fermati e chiedimi** invece di indovinare su: autenticazione `gh`, repository pubblico o privato,
nome del repository. Sono le tre cose che non puoi dedurre dal codice.
