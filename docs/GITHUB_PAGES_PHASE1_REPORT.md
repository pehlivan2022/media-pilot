# GitHub Pages — FASE 1 — Report

Data: 2026-08-30. Esito: **PASS**.

## Checklist

| Punto | Esito |
|---|---|
| FASE 0 — repo creato (`git init`, primo commit, `gh repo create`, push) | ✅ |
| `.gitignore` corretto (`data/*` con eccezione `pipeline_health.json`) prima del primo commit | ✅ |
| Repo pubblico `media-pilot`, deciso con l'utente (piano Free, no Pages da privato) | ✅ |
| `.env` fuori dal repo, verificato con `git check-ignore -v .env` | ✅ |
| Nessuna API key nei file versionati né nei log del workflow (582 righe di log ispezionate) | ✅ |
| `<meta name="robots" content="noindex">` su tutte le 11 pagine pubblicate | ✅ |
| Audit `docs/GITHUB_PAGES_DEPLOY_AUDIT.md` | ✅ |
| Workflow `.github/workflows/publish-pages.yml`, trigger solo `workflow_dispatch` | ✅ |
| Validazione JSON (sintassi, non vuoti, non zero byte) prima del deploy | ✅ |
| `deploy-manifest.json` generato con `generated_at`, `commit`, `sha256` per file | ✅ |
| Deploy con `actions/configure-pages` + `upload-pages-artifact` + `deploy-pages`, permessi `pages: write` / `id-token: write` | ✅ |
| Verifica dal vivo (11 pagine + 4 JSON reali → 200, checksum coerenti col manifest) | ✅ |
| Lancio manuale (`gh workflow run`) | ✅ |

## Esecuzione di test

- Run: [`33280928864`](https://github.com/pehlivan2022/media-pilot/actions/runs/33280928864) — conclusion `success`.
- Durata totale: **28 secondi** (build 6s, deploy 8s, verify 4s + code+cconfig overhead).
- Un primo tentativo (`33280907960`) è fallito allo step `Configure Pages` perché il sito Pages non era ancora abilitato sul repo — risolto con `gh api -X POST repos/pehlivan2022/media-pilot/pages -f build_type=workflow` (operazione una tantum, non serve rifarla ai run successivi).
- Le 11 pagine reali rispondono `200` dal vivo; `assets/data/deploy-manifest.json` elenca 9 file JSON con SHA256 verificati contro `rassegna.json`, `trending.json`, `signals.json`, `pipeline_health.json` scaricati dal sito pubblicato — tutti coincidenti.
- Nessuna corrispondenza per pattern di API key nei log del run.

## URL finale

**https://pehlivan2022.github.io/media-pilot/**

Nota: il repo è pubblico, quindi anche `config/`, `docs/` e il codice della pipeline sono visibili a chiunque su GitHub — decisione presa insieme all'utente in FASE 0.3. Le API key restano fuori (`.env` ignorato).

## Peso del sito pubblicato

~2.3 MB (11 pagine HTML + CSS + JS di shell/pagina + icone + 9 JSON + `pipeline_health.json`, incluso `embedded-data.js` da 584 KB tenuto come fallback).

## Cosa guardare dal telefono

1. Apri **https://pehlivan2022.github.io/media-pilot/** da Chrome/Safari mobile.
2. Verifica che le pagine si aprano e i dati (rassegna, trending, signals) siano quelli reali dell'ultimo run, non demo.
3. Controlla che il sito proponga "Aggiungi a schermata Home" (installabilità PWA — ora possibile perché servito in HTTPS, impossibile con `file://`).
4. Le card `alerts`, `archive`, `candidates`, `cases`, `tasks` mostreranno ancora dati demo fermi al 26 agosto: è atteso, non è un bug (vedi audit).

## Limiti incontrati

- `gh api user` non espone il campo `plan` con lo scope del token attuale — la decisione Free/Pro è stata confermata a voce, non verificata via API.
- GitHub Pages va abilitato una tantum sul repo (`build_type=workflow`) prima che `actions/configure-pages` possa completare il deploy — non documentato in modo ovvio nell'errore del primo run, richiesto un intervento manuale una sola volta.
- `embedded-data.js` (584 KB) è stato mantenuto nel deploy: non è stato specificamente testato se la dashboard funziona anche rimuovendolo, per evitare di rischiare una regressione senza un modo affidabile di verificarla in questa sessione. Da rivalutare se si vuole alleggerire il sito.
- `assets/data/candidates_source.json` è stato escluso dal deploy (non letto da nessuna pagina/JS, solo input di build) — discrepanza rispetto alla lista originale del task, segnalata nell'audit.

## Cosa serve per la FASE 2

Da `docs/TASK_GITHUB_PAGES_FASE1.md` (sezione STOP): esecuzione reale dello scraper su GitHub Actions, persistenza dello stato tra run, scheduler su fuso Europe/Sarajevo, e — solo in seguito — l'eventuale passaggio a hosting Aruba (playbook già pronto in `docs/TASK_GITHUB_ARUBA_FASE1.md`). Nessuno di questi punti è stato toccato in questa fase, come richiesto.
