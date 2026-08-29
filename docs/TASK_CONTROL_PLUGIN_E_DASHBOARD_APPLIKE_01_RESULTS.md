# RESULTS — control plugin + dashboard app-like

Stato: FASE 0, FASE 1 e FASE 2 fatte. Task completo.

---

# FASE 1 — control plugin: spese, fonti/keyword, scraping health, slash command

## 1a — Contabilità spese LLM

File nuovi: `config/pricing.yaml`, `pilot/spend.py`, `pilot/test_spend.py`.
File modificato: `pilot/llm.py` (aggiunto parametro `caller`, `check_cap()` prima della richiesta
HTTP fuori dal try/except esistente in modo che un tetto superato sollevi un errore vero invece di
degradare a `None`, `spend.record()` dopo ogni risposta riuscita con `usage.input_tokens`/
`output_tokens` — Anthropic — o `usage.prompt_tokens`/`completion_tokens` — DeepSeek).

- `data/spend.jsonl`: una riga JSONL per chiamata riuscita — `{ts, provider, model, in_tok,
  out_tok, usd, caller}`. Non esiste ancora perché nessuna chiamata LLM reale è stata fatta in
  questa sessione (`ls data/spend.jsonl` → non trovato, verificato).
- `config/pricing.yaml`: prezzi per `claude-sonnet-5` ($2.00/$10.00 per 1M, da skill `claude-api`
  di questo progetto, cache 2026-06-24) e `deepseek-v4-pro` ($0.435/$0.87 per 1M, da ricerca web —
  `api-docs.deepseek.com` non raggiunto direttamente in questa sessione, verificare quella pagina
  se i prezzi sembrano vecchi). `daily_usd_cap: null` di default — nessuna decisione di prodotto
  presa qui.
- `python -m pilot.spend --report [--days N]`: testato, funziona (nessuna riga da mostrare, spesa
  di oggi $0.0000 — verificato via `python -m pilot.manage status`).
- Test (`pilot/test_spend.py`, 4 test, tutti verdi): `cost_usd` sulle tariffe per milione,
  `cost_usd` su modello sconosciuto → 0.0 invece di crash, `check_cap()` solleva `RuntimeError`
  quando la spesa di oggi ≥ tetto, `check_cap()` no-op quando il tetto è `null`.

## 1b — Fonti e parole chiave (`pilot/manage.py`, nuovo)

Sottocomandi implementati, tutti testati dal vivo con `--dry-run` prima e verificati byte-per-byte
dopo: `add-source --id --name --url --type {rss,html} [--target] [--dry-run]`,
`add-keyword --term [--topic] [--dry-run]`, `list-sources [--enabled] [--target]`,
`check-sources`, `status`.

**Divergenza dal prompt trovata e non aggirata in silenzio**: `config/topics.yaml` non ha
raggruppamento per topic — è una singola lista piatta `weak_keywords` (verificato leggendo il
file per intero). Quindi `add-keyword --topic <topic> --term <parola>` non può scrivere "nel
topic giusto": `--topic` è accettato per compatibilità con la sintassi del prompt ma non ha
effetto, ogni termine finisce comunque in `weak_keywords`, con un avviso stampato a video. Se
serve raggruppamento per topic è una modifica di schema separata, non improvvisata qui.

**Scrittura testo mirata, non load→dump** (regola 0.2 del task): `add-source` inserisce il nuovo
blocco YAML subito prima della riga finale `count: N` di `sources.yaml` e incrementa quel numero;
`add_source_to_target` individua il blocco del target in `monitoring.yaml` per indentazione e
inserisce la nuova riga alla fine della sua lista `source_ids:`; `add-keyword` appende una riga a
`weak_keywords` in `topics.yaml`. Tutti i campi non forniti dall'utente (`last_verified_at`,
`items_7d_at_audit`, `window_actual_days`) sono scritti `null` — coerente con la regola di
progetto "dato non verificato = null" (§38 dell'handoff), non con i valori delle fonti esistenti
che sono stati misurati da un audit reale.

**Test round-trip richiesto dal task** (`pilot/test_manage.py`, 2 test): scrive una fonte finta in
`sources.yaml` e in un target di `monitoring.yaml`, verifica che TUTTE le righe preesistenti
restino identiche (confronto riga per riga escludendo solo il blocco/riga inserita), poi ripristina
il file e verifica l'uguaglianza byte-per-byte con l'originale. Eseguito realmente
(`python -m pilot.test_manage` e via `pytest`): **2/2 verdi**, file di config confermati puliti
dopo (`grep -c` per i marker di test → 0 in tutti e tre i file).

**Bug trovato e corretto**: `list-sources`/`check-sources`/`status` andavano in
`UnicodeEncodeError` su console Windows cp1252 quando un nome fonte contiene diacritici (es.
"Zvornički.ba", `đ`) — riprodotto dal vivo. Corretto con
`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` in cima a `pilot/manage.py`.

## 1c — Gestione scraping (buchi noti dello scheduler)

- **`pipeline_health.json` ora si scrive SEMPRE**, anche quando la pipeline si ferma a uno stadio
  o esplode un'eccezione (prima solo il successo scriveva il file — `_stop()` chiamava
  `sys.exit(1)` prima di arrivare alla scrittura). Nuovi campi: `run_finished_at`, `ok`,
  `failed_stage`, `error`, `sources_failed_detail` (kind/messaggio dell'ultimo errore HTTP per
  fonte, da `data/errors.jsonl`), `sources_zero_items`, `items_per_source`. Questo è il fix diretto
  al problema misurato in FASE 0: il run schedulato interrotto del 2026-08-29 alle 06:00 aveva
  lasciato `pipeline_health.json` fermo su un run precedente, invisibile all'utente. Verificato
  con un run reale (`python -m pilot.run_all --no-collect`, exit 0, 537.0s): il JSON ora contiene
  `"ok": true, "failed_stage": null, "run_finished_at": "..."`.
- **Catch-up**: `run_daily_pilot.bat` ora controlla `data\raw\<oggi>.jsonl` a inizio script; se
  esiste già, logga e esce (`exit /b 0`) senza rilanciare la raccolta di rete. Aggiunto un
  **secondo trigger giornaliero alle 12:00** allo stesso task Windows `MediaPilot_DailyAll`
  (`Set-ScheduledTaskTrigger`, verificato con `Get-ScheduledTask ... Triggers`: ora 2 trigger,
  06:00 e 12:00) — se il run delle 06:00 fallisce o viene interrotto (come misurato in FASE 0:
  `LastTaskResult 3221225786`/`STATUS_CONTROL_C_EXIT`), quello delle 12:00 trova il raw di oggi
  mancante e riprova; se le 06:00 sono andate bene, quello delle 12:00 si limita a loggare e uscire
  subito. **`StartWhenAvailable` era già `True`** sul task esistente (verificato con
  `Get-ScheduledTaskInfo`/`$task.Settings` — non serviva impostarlo, contrariamente a quanto
  assumeva il testo del task).
- **Rotazione log**: `run_daily_pilot.bat` ora rinomina `data\scheduler_run.log` in `.1` (sovrascrivendo
  il precedente `.1`) quando supera 5.242.880 byte (5 MB), prima di scrivere. Batch puro,
  `setlocal enabledelayedexpansion`, nessuna libreria.
- **`python -m pilot.manage status`**: implementato — stampa ultimo run/esito/durata, fonti
  ok/abilitate, fonti fallite (con dettaglio se presente), fonti a zero item, spesa LLM di oggi.
  Testato dal vivo (vedi output sopra).

**Non fatto, dichiarato**: non ho indagato la causa esatta di `STATUS_CONTROL_C_EXIT` sul run delle
06:00 di stamattina (FASE 0) — è un fatto misurato, non uno che questo giro di lavoro doveva
risolvere alla radice; il trigger di catch-up delle 12:00 e la scrittura sempre-vera di
`pipeline_health.json` sono la mitigazione richiesta dal task (catch-up + visibilità), non una
diagnosi della causa. Se si ripete, `pipeline_health.json` ora lo renderà visibile invece di
restare silenziosamente fermo su un run vecchio.

## 1d — Slash command (`.claude/commands/`)

Cinque file markdown nuovi, involucri sottili (la logica resta in Python): `mp-status.md`,
`mp-spend.md`, `mp-add-source.md`, `mp-add-keyword.md`, `mp-run.md`. Quelli di scrittura
(`mp-add-source`, `mp-add-keyword`) istruiscono sempre un passaggio `--dry-run` con conferma
dell'utente prima di scrivere davvero. `mp-run` non lancia nulla di propria iniziativa se l'utente
non specifica un target/priorità (una raccolta di rete dura minuti e tocca siti esterni).

## Test

`python -m pytest pilot/test_pipeline.py` → **25/25 verdi** (invariato, requisito del task
rispettato). `python -m pytest pilot/` (intero pacchetto, incluse le 6 nuove funzioni di test) →
**31/31 verdi**. Entrambi comandi eseguiti realmente in questa sessione.

## File creati

`config/pricing.yaml`, `pilot/spend.py`, `pilot/manage.py`, `pilot/test_spend.py`,
`pilot/test_manage.py`, `.claude/commands/mp-status.md`, `.claude/commands/mp-spend.md`,
`.claude/commands/mp-add-source.md`, `.claude/commands/mp-add-keyword.md`,
`.claude/commands/mp-run.md`.

## File modificati

`pilot/llm.py` (caller + tetto di spesa + registrazione costo), `pilot/run_all.py` (health scritto
sempre, con più dettaglio), `run_daily_pilot.bat` (catch-up idempotente + rotazione log). Task
Windows `MediaPilot_DailyAll`: aggiunto un secondo trigger giornaliero (12:00).

## Rischi residui

- I prezzi DeepSeek in `config/pricing.yaml` vengono da un aggregatore di terze parti, non dalla
  pagina ufficiale `api-docs.deepseek.com` (non raggiunta in questa sessione) — verificarli prima
  di fidarsene per un tetto di spesa reale.
- Il tetto di spesa (`daily_usd_cap`) è `null`: nessun limite attivo finché l'utente non ne
  imposta uno.
- `add-source` scrive `owner_group: null`, `last_verified_at: null`, `items_7d_at_audit: null`,
  `window_actual_days: null` per ogni fonte aggiunta a mano: onesto (nessun dato inventato), ma
  significa che una fonte aggiunta così non compare come "verificata" finché non gira almeno un
  collect reale — `check-sources`/`list-sources` non segnalano questa differenza rispetto alle
  fonti da audit.
- La causa di `STATUS_CONTROL_C_EXIT` sul run delle 06:00 di ieri resta non diagnosticata (vedi
  sopra).

---

# FASE 2 — dashboard app-like, mobile per primo

## Scoperta iniziale: gran parte era già fatta

Prima di scrivere codice ho letto `app.css`/`header.js`/`index.html`. **Bottom tab bar mobile,
"Meni" a bottom-sheet (riuso di `.sheet`/`.sheet-overlay`), `env(safe-area-inset-bottom)` sulla
tab bar, `overflow-x:hidden`, touch target ≥44px (già 62px) erano già implementati** — non li ho
ricostruiti, solo verificati. Quello che mancava davvero, verificato leggendo `app.css` per
intero (`grep` su `viewport-fit`, `tap-highlight`, `overscroll`, `view-transition`):

1. **`viewport-fit=cover` mancava nel meta viewport di tutte le pagine** — senza, `env(safe-area-
   inset-bottom)` (già scritto in CSS) risolve sempre a `0px`, quindi il padding sicuro non aveva
   mai effetto reale su iPhone con notch/home indicator nonostante il CSS ci fosse. Aggiunto a
   tutte le 11 pagine reali (`index/us/vrh/media/case/eksperti/konkurenti/ostali/arhiva/go/
   simulator.html`), non toccati `_selftest*.html` e le preview in `data/` (fuori scope).
2. **`-webkit-tap-highlight-color:transparent`** mancava — aggiunto su `a`/`button` globalmente.
3. **`overscroll-behavior`** mancava — `none` su `html,body` (contenitore di scroll principale),
   `contain` su `.sheet` (contenitore di scroll indipendente, per non propagare l'overscroll al
   body quando la sheet è al suo limite).
4. **`@view-transition{navigation:auto}`** mancava — aggiunto in cima a `app.css`, due righe,
   degrada a niente sui browser che non lo supportano (nessuna libreria).
5. **Header non si comprimeva mai allo scroll** (era già compatto, 60px, non "mezzo schermo", ma
   restava fisso a quell'altezza) — aggiunta una classe `body.scrolled` (soglia `scrollY>8`,
   ascoltatore in `header.js::watchScroll()`, chiamato una volta da `mount()`) che porta
   `.topbar` a 44px e nasconde il sottotitolo; rispetta già la regola globale
   `prefers-reduced-motion` esistente in `app.css` (nessuna aggiunta necessaria lì).

**Non toccato**: architettura multipagina (nessun router SPA), `.media-tabs`/`.media-cols`,
`dashboard-config.js`, la logica di `isActive()` in `header.js` (usa `location.pathname`, non
`document.body.dataset.page` come ipotizzava il prompt — verificato che `data-page` esiste su
ogni pagina ma non è usato per lo stato attivo; il comportamento finale è identico, riscriverlo
avrebbe solo rischiato di rompere qualcosa senza cambiare nulla per l'utente, quindi lasciato
com'era).

## PWA

**Passo 1 fatto** (aspetto nativo, zero service worker/manifest — quanto sopra). **Passo 2 non
fatto**, come da istruzioni del task ("proponimelo, non farlo di iniziativa"): se vuoi l'icona
sulla home dello smartphone serve `manifest.webmanifest` + service worker minimo + `serve.bat`
(`python -m http.server`), inerte su `file://`. Dimmi se lo vuoi.

## Verifica reale (non solo ispezione)

Il tool di automazione browser **non può navigare `file://`** (bloccato esplicitamente, verificato
provando) e **non riesce a ridimensionare la finestra reale del browser** in questo ambiente
(`resize_window` a 375×812 non cambia `window.innerWidth`, resta 1920 — verificato due volte, su
due tab diverse). Per verificare comunque il comportamento reale, senza toccare il funzionamento
`file://` di produzione, ho avviato un server HTTP temporaneo solo per il test
(`python -m http.server 8791` sulla cartella del progetto, fermato e verificato spento a fine
verifica — porta 8791 confermata libera dopo) e ho forzato via CSS iniettato la visibilità della
bottom-nav per ispezionarla (il contenuto sotto è comunque quello vero, `assets/data/*.json`
reali — si vede "Branko Blanuša +433% momentum", i Signal REVIEW reali, ecc.):

- **Nessun errore in console** al caricamento e dopo le interazioni (verificato con
  `read_console_messages`, prima e dopo un refresh per catturare gli errori di caricamento).
- **Nessuno scroll orizzontale**: `document.documentElement.scrollWidth` (1905) ≤
  `window.innerWidth` (1920), verificato via JS.
- **Bottom tab bar**: 5 colonne (Radar/US/Konkurenti/Teritorij/Meni), stato attivo evidenziato
  correttamente sulla pagina corrente (screenshot).
- **Sheet "Meni"**: si apre riusando `.sheet`/`.sheet-overlay` esistenti, elenco corretto,
  si chiude col tasto ×  (screenshot).
- **Scroll-compress header**: verificato con JS che `body.scrolled` si attiva/disattiva
  correttamente scrollando giù/su, e che `.topbar` passa da min-height 60px a 44px quando attivo
  (screenshot prima/dopo — l'evidenza visiva più significativa di questo giro, dato che il resto
  della UI mobile esisteva già).

**Non verificato con uno screenshot a 375×812 vero**: limite dell'ambiente di automazione (sopra),
non del codice — il CSS per il breakpoint mobile (`@media(min-width:769px)`) non è stato toccato
in questo giro, solo le proprietà elencate sopra, quindi il rischio di regressione sulla vista
mobile reale è basso ma non verificato con uno screenshot a quella dimensione esatta. Consiglio:
controllalo tu una volta sul telefono reale o con devtools locali (`F12` → device toolbar), che
non hanno questa limitazione.

## Test

Nessun test Python toccato da FASE 2 (solo HTML/CSS/JS). `python -m pytest pilot/` non rilanciato
qui perché nessun file `pilot/` è stato modificato in questa fase — invariato dai 31/31 di FASE 1.

## File modificati (FASE 2)

`app.css` (view-transition, tap-highlight, overscroll-behavior, scroll-compress header),
`header.js` (funzione `watchScroll()`), le 11 pagine HTML reali (meta viewport
`viewport-fit=cover`).

## Rischi residui (FASE 2)

- Vista mobile reale (375×812) non verificata con uno screenshot autentico per il limite del tool
  di automazione descritto sopra — verificarla su un dispositivo o devtools reali prima di
  considerarla definitiva.

---

# FASE 2, passo 2 — PWA (installabilità), su richiesta esplicita dopo la proposta

File nuovi: `manifest.webmanifest`, `sw.js` (service worker minimo, cache-first sulla shell
statica, MAI su `assets/data/*.json` — i dati restano sempre da rete), `pwa.js` (registrazione,
**guard esplicito `location.protocol === 'file:'` → non registra nulla**, oltre al fatto che i
service worker non si registrano comunque su `file://` per spec del browser), `serve.bat`
(`python -m http.server 8000`, opzionale, solo per installare l'app), `assets/icons/icon-192.png`,
`assets/icons/icon-512.png`, `assets/icons/apple-touch-icon.png` (generate con Pillow, già
presente sulla macchina — non aggiunta a `requirements.txt`, non usata da nessun modulo `pilot/`,
solo uno script una tantum per produrre 3 PNG statici; stesso marchio "US" viola già usato in
`header.js`/`app.css`).

Aggiunto a tutte le 11 pagine reali: `<link rel="manifest">`, `<link rel="apple-touch-icon">`,
`<meta name="theme-color">`, `<script src="pwa.js">`.

**Verificato dal vivo** (server HTTP temporaneo su porta 8792, fermato e porta confermata libera
dopo): `fetch('manifest.webmanifest')` → 200; `navigator.serviceWorker.ready` → `active.state ===
'activated'`; zero errori console. Il doppio click su `file://` resta identico a prima (il guard in
`pwa.js` impedisce anche solo il *tentativo* di registrazione su quell'origine).

## File per Aruba File Manager

Consegnato `media-pilot-dashboard.zip` (~395 KB, 46 file) — **solo la dashboard statica**:
11 pagine HTML reali, `app.css`, tutti i JS di shell/pagina, `manifest.webmanifest`, `sw.js`,
`pwa.js`, le icone PWA, `assets/data/*.json` reali (esclusa `rassegna.json.demo-backup`, non
serve online) e `data/pipeline_health.json` (alimenta la card di stato). **Esclusi
deliberatamente**: `.env` (chiavi API — mai da esporre pubblicamente), `pilot/` (backend Python,
non ha senso su un hosting statico), `config/`, `data/raw|*.jsonl|*.db|*.log`, `docs/`, `.claude/`,
i `*.bat` locali, `tools/`, `input/` — niente di tutto questo serve al browser dell'utente finale e
alcuni conterrebbero dati interni non destinati alla pubblicazione. Struttura dello zip già piatta
(nessuna cartella wrapper): va estratto direttamente nella root dello spazio web (es.
`public_html/`), `index.html` deve restare alla radice.

**Nota**: questo pacchetto è una FOTOGRAFIA dei dati reali al momento della consegna (rassegna
1.080 item, trending 26 entità, signals 20 REVIEW). Non si aggiorna da solo una volta su Aruba: la
pipeline (`pilot/`) resta locale, e ogni volta che gira va ricaricato lo zip aggiornato (o solo
`assets/data/*.json` + `data/pipeline_health.json`) per rinfrescare i dati online — questo giro di
lavoro non ha costruito un deploy automatico verso Aruba, non richiesto e fuori scope.
