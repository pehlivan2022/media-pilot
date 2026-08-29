# TASK — Control plugin (scraping / spese / fonti) + dashboard app-like

Prompt per Claude Code. Si incolla intero. Repo di lavoro:

```
C:\Users\frontofficedx\Desktop\NIK 2026\US\________media-pilot-v21-2026-08-26\media-pilot-v21-simple
```

---

## 0. Regole non negoziabili

1. **Zero nuove dipendenze.** `requirements.txt` resta com'è. In particolare **mai `import yaml`**:
   il progetto ha `pilot/miniyaml.py` apposta. Frontend: niente framework, niente build step,
   niente npm — la dashboard è HTML+JS vanilla aperta anche con doppio click.
2. **`config/` è scritto a mano e pieno di commenti che valgono.** Es. il commento su
   `priority: pilot` in `monitoring.yaml` documenta una proprietà di sicurezza di argparse.
   Qualsiasi scrittura automatica su YAML **deve preservare commenti, ordine e formattazione**:
   si appende o si edita in-place a livello di testo, **non** si fa load → dump.
3. **Non toccare** `pilot/score.py`, `config/scoring.yaml`, `config/entities.yaml` senza chiedermelo
   prima ed esplicitamente.
4. **`python -m pytest pilot/test_pipeline.py` deve restare 19/19 verde** a fine lavoro.
5. **Niente numeri inventati.** Ogni cifra nel report finale deve venire da un comando eseguito
   davvero, con il comando citato accanto.

---

## FASE 0 — Riassunto del progetto (verificato, non narrato)

Produci `docs/PROJECT_SUMMARY_2026-08-29.md`: massimo 2 pagine, in italiano.

Leggi come **punto di partenza** (non come verità): `docs/FINAL_PROJECT_STATUS.md`,
`docs/HANDOFF_PROGRESS.md`, `docs/MEDIA_PILOT_FINAL_HANDOFF.md`,
`docs/MEDIA_PILOT_NEXT_TASKS_AFTER_BETA02.md`, `docs/TASK_WINDOWS_SCHEDULER_01_RESULTS.md`,
`docs/B1_RESULTS.md`, `docs/B3_RESULTS.md`, `docs/dashboard-data-contract.md`.

Poi **verifica ogni affermazione contro il codice in `pilot/` e i file in `data/` e
`assets/data/`**. La lezione della sessione precedente è esattamente questa: i report descrivono
lo stato che si voleva, non sempre quello che c'è. Dove doc e codice divergono, scrivilo in chiaro
in una sezione "Divergenze doc ↔ codice".

Il riassunto deve rispondere a:
- Cosa fa la pipeline, stadio per stadio (`collect → clean → dedup → score → trending → signals →
  export_dashboard`), con i **numeri reali dell'ultimo run** (item raccolti, dopo dedup, cluster).
- Cosa c'è in `config/` e chi lo scrive (a mano vs generato).
- Come la dashboard riceve i dati (contratto `assets/data/*.json`, fallback `embedded-data.js`),
  e **quali file JSON sono ancora demo** e quali sono reali.
- Stato dello scheduler `MediaPilot_DailyAll` e i suoi buchi noti.
- Cosa è aperto: contaminazione temporale, task residui post-beta.

---

## FASE 1 — "Control plugin": gestione scraping, spese, fonti e parole chiave

### Assunzione già risolta (non riaprirla)

La dashboard è composta da file statici senza backend e funziona anche via `file://`
(`data.js` fa fetch e ricade su `window.__MP_EMBEDDED__` quando il fetch fallisce). **Una pagina
del browser quindi non può scrivere `config/*.yaml`.** Perciò il "plugin" è:

- **superficie di comando = CLI Python + slash command Claude Code** in `.claude/commands/`;
- **superficie dashboard = sola lettura** (una card di stato/spesa alimentata dal JSON che il
  pilot esporta).

Questo rispetta anche la filosofia già scritta in `pilot/run_monitor.py`: *"non costruire un
orchestratore interno complesso"*.

### 1a — Contabilità spese LLM (`pilot/spend.py`, nuovo)

**Stato attuale verificato: non esiste alcun tracciamento di costo.** `pilot/llm.py` non legge
`usage` e non conta né token né denaro. È tutto da fare, ma piccolo:

- Un wrapper attorno a `llm()` che, a ogni chiamata, legge `usage.input_tokens` /
  `usage.output_tokens` dalla risposta API e appende **una riga JSONL** a `data/spend.jsonl`:
  `{ts, provider, model, in_tok, out_tok, usd, caller}`.
- Prezzi per modello in `config/pricing.yaml` (nuovo, scritto a mano, commentato con la data in cui
  i prezzi sono stati letti — così quando cambiano si sa che sono vecchi).
- Un tetto di spesa opzionale in `config/pricing.yaml` (`daily_usd_cap`): superato il tetto,
  `llm()` **solleva un errore chiaro invece di chiamare l'API**. Nessun degrado silenzioso.
- Comando `python -m pilot.spend --report [--days N]`: totale, per modello, per giorno, per caller.

**Delimita l'ambito:** questo ledger copre **solo il denaro delle API LLM**. Il volume di richieste
di scraping per fonte (quante fetch, quanti errori HTTP, quanti item per fonte) è un'altra cosa e
va nella salute pipeline del punto 1c — dillo esplicitamente nel report, così non si confondono.

### 1b — Inserimento fonti e parole chiave (`pilot/manage.py`, nuovo)

Sottocomandi che scrivono `config/sources.yaml`, `config/topics.yaml` e `config/monitoring.yaml`
**preservando commenti e formattazione**:

- `python -m pilot.manage add-source --id <ID> --name <nome> --url <url> --type <tipo> [--target <id>]`
  — valida che l'ID non esista già, appende la voce nella sezione giusta, e se passi `--target`
  aggiunge l'ID anche a quel target di `monitoring.yaml`.
- `python -m pilot.manage add-keyword --topic <topic> --term <parola>` — su `topics.yaml`.
- `python -m pilot.manage list-sources [--enabled] [--target <id>]` e `check-sources` (fonti
  presenti in `monitoring.yaml` ma inesistenti in `sources.yaml`, e viceversa fonti mai usate da
  nessun target).
- `--dry-run` su tutti i comandi di scrittura: stampa il diff e non tocca niente.

**Lascia un test eseguibile** che dimostri il round-trip non distruttivo: leggi `monitoring.yaml`,
scrivi una fonte finta, verifica che tutti i commenti e le righe preesistenti siano identici byte
per byte tranne l'inserimento, poi rimuovila. Un `assert`, nel file di test già esistente o in un
`test_manage.py` piccolo — niente fixture, niente framework nuovo.

### 1c — Gestione dello scraping (i buchi noti dello scheduler)

Da `docs/TASK_WINDOWS_SCHEDULER_01_RESULTS.md`, già documentati come limiti accettati — ora sono
il backlog, non scoperte da rifare:

1. **Gira solo se l'utente è loggato**, `RunLevel: Limited`, nessuna password salvata.
2. **Nessun recupero**: PC spento alle 06:00 = quel giorno salta, in silenzio.
3. **`data/scheduler_run.log` è append-only, senza rotazione.**

Da fare, nell'ordine, il più economico prima:
- **Catch-up**: all'avvio, `run_daily_pilot.bat` (o meglio `run_monitor.py`) controlla se esiste
  `data/raw/<oggi>.jsonl`; se manca ed è passata l'ora prevista, gira. Aggiungi il trigger
  `StartWhenAvailable` al task di Windows così Windows stesso recupera i run persi.
- **Rotazione log**: quando `scheduler_run.log` supera ~5 MB, rinomina in `.1` e riparti. Poche
  righe, nessuna libreria.
- **Health**: estendi `data/pipeline_health.json` con l'esito dell'ultimo run (ts inizio/fine, exit
  code, item per fonte, fonti a zero item, errori HTTP) — è questo il file che alimenta la card
  della dashboard.
- Comando unico `python -m pilot.manage status`: ultimo run, esito, fonti mute, spesa di oggi.

### 1d — Slash command Claude Code (`.claude/commands/`)

Sottili, solo involucri dei comandi sopra — la logica sta in Python, non nel markdown:
`/mp-status`, `/mp-spend`, `/mp-add-source`, `/mp-add-keyword`, `/mp-run`.

---

## FASE 2 — Dashboard app-like, mobile per primo

### Vincolo strutturale (non riscrivere l'architettura)

La dashboard è **multi-pagina**: ogni sezione è un `.html` con i suoi `<script>`
(`index/vrh/us/media/case/eksperti/konkurenti/ostali/arhiva/go/simulator`). **Non convertirla in
una SPA con router.** L'effetto app si ottiene con:

- **Bottom tab bar persistente** su mobile (le 4-5 destinazioni vere, non tutte e 11), con lo stato
  attivo derivato da `document.body.dataset.page` — che c'è già.
- **Safe area**: `viewport-fit=cover` nel meta e `env(safe-area-inset-bottom)` nel padding della
  tab bar, altrimenti su iPhone la barra finisce sotto la home indicator.
- **Target touch ≥ 44px**, `-webkit-tap-highlight-color: transparent`, `overscroll-behavior: none`
  sui contenitori scrollabili.
- **Transizioni tra documenti**: `@view-transition { navigation: auto; }` — due righe di CSS, degrada
  a niente sui browser che non la supportano.
- **Riusa le primitive che ci sono già** in `app.css`: `.sheet` / `.sheet-overlay` /
  `.sheet-handle` (bottom sheet mobile che diventa modale da 769px) e il pattern `.media-tabs`.
  Non inventarne di nuove.
- Header: comprimibile allo scroll, non fisso a occupare mezzo schermo.

### PWA: opzionale e condizionata (leggi prima di promettere l'installabilità)

`data.js` è scritto apposta per funzionare con il **doppio click su `file://`**. Su `file://` un
service worker **non si registra**, quindi l'installazione vera dell'app è impossibile senza
servire la cartella. Quindi:

- **Passo 1 (fallo):** aspetto e comportamento nativi. Zero service worker, zero manifest.
  Il doppio click continua a funzionare identico. Questo è il grosso del guadagno percepito.
- **Passo 2 (proponimelo, non farlo di iniziativa):** `manifest.webmanifest` + service worker
  minimo + un `serve.bat` con `python -m http.server` — solo se voglio l'icona sulla home dello
  smartphone. Se lo fai, il codice deve restare inerte su `file://`, non rompere il doppio click.

### Verifica

Prova a 375×812 (mobile) e in desktop, con la dashboard **aperta da file** e con i dati reali di
`assets/data/`. Niente scroll orizzontale, niente tap target minuscoli, nessun errore in console.
Screenshot prima/dopo della home in mobile.

---

## Ordine di lavoro e consegna

Fase 0 → 1a → 1b → 1c → 1d → 2. Fermati e chiedimi conferma **dopo la Fase 0** e **dopo la Fase 1**,
prima di partire con la successiva.

A fine lavoro scrivi `docs/TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01_RESULTS.md` con:
comandi realmente eseguiti e loro output, file creati/modificati, esito di
`python -m pytest pilot/test_pipeline.py`, cosa **non** hai fatto e perché, e i rischi residui.

Se durante il lavoro trovi che una parte di questo prompt è sbagliata rispetto al codice reale,
**fermati e dimmelo** invece di adattare il codice al prompt.
