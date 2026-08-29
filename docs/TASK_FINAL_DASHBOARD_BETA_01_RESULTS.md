# TASK FINAL DASHBOARD BETA 01 — RESULTS

Date: 2026-08-29. Chiude §J di `docs/FINAL_PROJECT_STATUS.md` ("wiring dei semafori/detail
view ai dati reali — non fatto"). Frontend canonico aggiornato in place: nessuna copia
(`index-new.html`, `dashboard-v2.html`), nessun nuovo framework/build/backend (§19), nessun
file `pilot/**`/`config/**`/`*.jsonl` toccato.

---

## File modificati

| file | cosa e' cambiato |
|---|---|
| `radar.js` | `cardStatus(card, items, signals)` riscritto: grigio/verde/ambra da `rassegna.json` + `signals.json` REVIEW reali, non piu' dalla catena demo `alerts()/cases()` (richiedeva `developer_info.risk_score`, assente sui dati reali). `rankCards` inoltra `signals`. |
| `ui.js` | `wireDashboardCards`/`openDashboardCard` inoltrano `signals`. `cardSheetBody`: rimossa `risk X/5` (§4.2/§5, "niente score tecnico"), aggiunto stato `grey`, titoli evento linkati a `item.url` reale (evidence, §5). |
| `data.js` | `loadAll()`: isolamento per-file (un 404 non fa piu' cadere tutto su `__MP_EMBEDDED__`), `__missing[]` esposto, `pipeline_health.json` (fuori da `assets/data/`) caricato nello stesso giro. Fallback embedded resta identico SOLO se TUTTI i file falliscono (scenario `file://`). |
| `store.js` | + `navCollapsed` (persistito, stesso prefisso `mp_v21:`), `setNavCollapsed()`. |
| `header.js` | nav desktop: icona+label (`nav-ico`/`nav-label`) per supportare il collasso. Bottone menu in `.topbar-actions`: ≥769px collassa la sidebar, <769px apre il drawer esistente (`menuSheet`, invariato). Stato collassato applicato a `mount()` da `Store` (persiste tra pagine, header.js e' condiviso). |
| `app.css` | + `.status-grey`/`.dot-grey`; stato `body.nav-collapsed` dentro il blocco `@media(min-width:769px)` esistente (sidebar 196px→60px, label nascosta, `#page-content`/`.topbar` riallineati); + `.status-line`/`.home-list`/`.home-list-row` per le nuove sezioni home. `.status-blue`/`.dot-blue` lasciati (dead code innocuo, non piu' referenziati da JS). |
| `page-us.js`, `page-konkurenti.js`, `page-go.js`, `page-ostali.js` | `corpus=UI.buildCorpus(data)` (rassegna+cases demo) → `items=data.rassegna` reale + `signals=data.signals`, passati a `rankCards`/`wireDashboardCards`/`pageHead`. |
| `page-home.js` | riscritto: 4 sezioni nuove (stato pipeline, Trending adesso, Da gledati, Ultime vijesti) + le 4 sezioni card esistenti ora su dati reali. Pannello VRH lasciato su `UI.buildCorpus` invariato (demo, fuori scope §25). |
| `_selftest_beta.html` | **nuovo**. Autotest §22 (13 item) contro i dati reali via http, stesso pattern visivo di `_selftest.html` (righe pass/fail + summary), non lo sostituisce (quello resta com'e', copre altro). |
| `docs/FINAL_PROJECT_STATUS.md` | riga §J aggiornata (vedi sotto). |

Non toccati (per costruzione, verificato): `pilot/**`, `config/**`, `data/*.jsonl`, schema dei
4 JSON, `alerts.json`/`cases.json`/`tasks.json`/`archive.json`/`candidates.json` e le pagine che
li consumano (`page-vrh.js`, `page-case.js`, `page-eksperti.js`, `page-media.js`,
`page-simulator.js`, `case.html`, `vrh.html`, `eksperti.html`, `media.html`, `simulator.html`) —
verificate live, zero errori console, comportamento demo Alert/Case/VRH invariato.

## Componenti riusati (nessuno nuovo)

`UI.openSheet` per ogni nuovo dettaglio (pipeline, entita' Trending, Signal, liste "Vedi sve") —
zero pagine nuove oltre `_selftest_beta.html`. Menu drawer mobile: `Header.menuSheet()`
esistente, invariato, ora richiamato anche dal nuovo bottone desktop quando `innerWidth<769`.
`RadarEngine.cardItems()` invariato (gia' compatibile con lo schema reale). `.badge`/`.badge-alert`
per il badge REVIEW. `.home-vrh-row-title`/`.home-vrh-row-meta` riusate per le righe compatte di
Trending/Signal/Rassegna (nuove sole `.status-line`/`.home-list`/`.home-list-row`, wrapper
generici, non un secondo sistema di liste).

## Regole semafori (come implementate, §3)

`RadarEngine.cardStatus(card, items, signals)`:
- **grigio**: `last7.length===0` (nessun item `rassegna.json` per la card negli ultimi 7 giorni).
- **verde**: attivita' in rassegna ma nessun Signal REVIEW per l'entita'.
- **ambra**: >=1 riga di `signals.json` con `entity_id===card.key` o `card.key` in `entities[]`
  — match diretto sulla chiave gia' condivisa tra `dashboard-config.js` e il registry entita'
  del pilot (confermato in `TASK_BETA_03_RESULTS.md` D2), nessun nuovo mapping inventato.
- **rosso**: MAI assegnato da questa funzione (nessun path di codice lo produce). Resta uno
  stato supportato da label/CSS, riservato a una futura fonte di Alert umano/confermato —
  verificato live con `_selftest_beta.html` test 13: **55 card reali (US+KONKURENTI+OSTALI+
  TERITORIJ), 0 in rosso**.

Sul dataset reale attuale (683 item rassegna, 17 Signal REVIEW): card US ha
`us-snsd`/`stevandic` in ambra, `us`/`us-sps`/`mandati-us` verdi, le 9 card "nosilac lista IJ"
senza attivita' recente in grigio — coerente con l'audit D2.1 di `TASK_BETA_03_RESULTS.md` (le
stesse card senza `modules` mappati restano senza segnale, atteso).

## JSON reali collegati

| file | dove |
|---|---|
| `assets/data/rassegna.json` (683 item) | semafori (tutte le 4 pagine card + home), sezione "Ultime vijesti" home (12 piu' recenti) |
| `assets/data/trending.json` (24 entita' attive) | sezione "Trending adesso" home (5-8 righe, ordinate momentum→fonti→eventi→mentions→recency) |
| `assets/data/signals.json` (17 REVIEW) | ambra sui semafori + sezione "Da gledati" home (3-5 righe, confidence→last_seen) |
| `data/pipeline_health.json` | strip stato home (ONLINE/DEGRADED, ultimo run, fonti attive) |

## Menu / collapse

Struttura menu **invariata** (Radar/US/Konkurenti/Teritorij/Ostali/VRH/Arhiva) — decisione presa
prima di scrivere codice: l'ordine suggerito in §11 (Rassegna/Trending/Signal/Archivio/Fonti/Stato
sistema) e' "suggerito", §0/§14 impongono di riusare pagine reali gia' funzionanti, non di
ricostruire la navigazione. Rassegna/Trending/Signal diventano **sezioni della HOME** (§6-§9
parlano di contenuto, non di route). "Fonti" omesso: nessuna vista fonti reale esiste, §11
permette di ometterla piuttosto che inventarla.

Sidebar desktop (≥769px): bottone ☰ in topbar toggla `body.nav-collapsed`, 196px→60px, icone
sempre visibili, label nascoste da collassata, persistito per-browser via `Store`
(`localStorage mp_v21:navCollapsed`) — verificato dal vivo: sopravvive a un reload della pagina.
Mobile (<769px): nessuna sidebar permanente (gia' cosi'), stesso bottone apre il drawer
`menuSheet()` esistente (verificato dal vivo via chiamata diretta al componente — vedi limiti
sotto).

## Responsive testato

1920px: verificato dal vivo (screenshot), sidebar/collapse/click-through tutti confermati.
390/768/1280px: **non verificabile dal vivo in questa sessione** — `resize_window` del tool di
automazione browser non ha cambiato `window.innerWidth` (rimasto 1920 dopo la chiamata, ambiente
con finestra Chrome massimizzata dal sistema, fuori dal nostro controllo). Il drawer mobile e'
comunque stato verificato funzionante chiamando direttamente `menuSheet()` (component-level, non
via breakpoint reale) — vedi sezione Test sotto. Le regole CSS mobile (`.mobile-nav`,
`.navbar{display:none}` sotto 769px) non sono state toccate da questo giro di modifiche (le
uniche righe nuove vivono dentro il blocco `@media(min-width:769px)` gia' esistente), quindi il
comportamento mobile pre-esistente (gia' verificato nelle Beta precedenti) non e' a rischio per
costruzione — ma non e' stato ri-fotografato a 390/768px qui. **Limite dichiarato**, non nascosto.

## Test (§22)

`_selftest_beta.html`, eseguito via http (`python -m http.server`): **13/13 pass**. Dettaglio
rilevante:
- #6: 15 card US, livelli reali (`green`/`orange`/`grey`), nessun `blue` residuo.
- #9/#10: sheet apre/chiude, link evidence trovato con `target=_blank rel=noopener` e href reale.
- #11: isolamento per-file replicato dal vivo (fetch reale + 1 path inesistente): gli altri due
  file restano `ok=true` mentre il path finto fallisce da solo.
- #13: 55 card reali, **0 rosso**.

Console browser (`read_console_messages`, `onlyErrors`): **zero errori** su
`index.html`/`us.html`/`konkurenti.html`/`go.html`/`ostali.html`/`vrh.html`/`media.html`/
`eksperti.html`/`arhiva.html`, verificato dal vivo dopo ogni navigazione.

## Scelte deliberate / rimandato

- **Filtri sulla sezione Rassegna (§8)**: non costruiti. La spec permette esplicitamente di
  saltare "un sistema di ricerca complesso"; la lista compatta (12 righe piu' recenti) copre il
  bisogno immediato della Beta. Aggiungere se richiesto: filtro per fonte/entita' sopra
  `rassegnaRowHtml` in `page-home.js`, dati gia' disponibili in `item.source_note`/`modules`.
- **Numeri Trending sulla card (§4.2, "facoltativo")**: non aggiunti a ogni card-orb (avrebbe
  richiesto passare una mappa `entity_id→trending` a 5 file per un dato gia' visibile nella
  sezione "Trending adesso" dedicata). Il dato esiste ed e' mostrato, solo non duplicato sulla
  card.
- **`sources_ok`/`sources_failed`** sono `null` in `pipeline_health.json` oggi (pipeline non
  ancora instrumentata per quel dettaglio — pre-esistente, non introdotto qui). La strip mostra
  `"N izvora aktivno"` invece di un rapporto OK/KO fabbricato, come da regola "dato mancante =
  null, mai inventato" (§21).
- **"Vedi sve" su Rassegna**: omesso (nessun link, solo le 12 righe compatte) — la spec lo rende
  facoltativo ("oppure omettere il link se la lista compatta basta"); Trending/Signal HANNO
  invece "Vedi sve" (sheet con lista completa) perche' i file sorgente possono superare la soglia
  mostrata.
- **`.status-blue`/`.dot-blue`** in `app.css`: lasciati, non piu' referenziati da nessun JS dopo
  questa modifica — dead code innocuo, rimuoverlo non cambia comportamento, non fatto per tenere
  il diff piccolo.

## Definition of Done — riscontro

Tutti i punti di §23 soddisfatti salvo: responsive 390/768/1280px non ri-verificato dal vivo
(limite ambiente, vedi sopra — CSS non toccato a quei breakpoint). Tutti gli altri punti
verificati dal vivo in questa sessione (semafori come elemento principale, menu collassabile
desktop, drawer mobile — component-level, 4 JSON reali collegati, cap 5-8/3-5 rispettati, click
semaforo→dettaglio/evidence, nessun dato inventato, nessun ROSSO automatico, nessun framework
nuovo, console pulita, DEMO separato dal REAL).
