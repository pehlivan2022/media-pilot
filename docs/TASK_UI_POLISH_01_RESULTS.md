# TASK_UI_POLISH_01 — Risultati

Repository reale: `pehlivan2022/media-pilot` (locale: `C:\Users\frontofficedx\Desktop\media-pilot`).

## Incidente da segnalare

La prima esecuzione di questo task è avvenuta per errore in
`Desktop\NIK 2026\US\________media-pilot-v21-2026-08-26\media-pilot-v21-simple` — una copia locale
non collegata a questo repository, ferma al 26 agosto. Il file `TASK_UI_POLISH_01.md` che avevo
ricevuto in `Downloads` non conteneva l'avviso "cartella giusta" presente in questa copia in
`docs/`; l'ho scoperto solo al momento di pubblicare, confrontando i contenuti coi remote GitHub.
Tutto il lavoro di quella sessione è stato rifatto da capo qui, contro il vero `app.css` (che nel
frattempo aveva già ricevuto un commit indipendente, `9cb39c1`, con fix separati su scroll mobile,
font e colori status). Nessuna modifica di quella sessione era arrivata su git o online — il sito
live non era mai stato toccato.

## Stato di partenza reale (verificato in `app.css`, non nella copia sbagliata)

A differenza di quanto sembrava dalla copia sbagliata, qui il documento task risulta accurato:

- `--muted:#73808c` su `--bg:#f3f5f7` → **3,70:1**, sotto soglia AA. Confermato.
- `body{font-size:16px;line-height:1.42}` (il `16px` era già stato fissato dal commit 9cb39c1,
  `line-height` no).
- `touch-action:manipulation` **assente** ovunque. Confermato.
- `backdrop-filter:blur(8px)` su `.topbar` **presente e attivo**. Confermato.
- `<meta name="theme-color" content="#7b4b9e">` **e** `viewport-fit=cover` **già presenti** in
  tutte le 11 pagine (qui la "NON rifare" del task era corretta — il viewport-fit c'era già, andava
  aggiunto solo lo sdoppiamento chiaro/scuro).
- `orbFloat`: dichiarato attivo ma già neutralizzato da `animation:none` più giù nel file (V21.3) —
  dead code, non visibile. Ripulito comunque.
- Ombra condivisa: qui esiste davvero, ma con nome `--shadow-soft` (non `--shadow-card` come scritto
  nel task) su `.topbar,.navbar,.mobile-nav,.card,.vrh-card,.sheet,.btn,.today-chip` — di questi,
  `.card` e `.today-chip` erano gli unici due la cui ombra arrivava fino in fondo invisibile
  (`background:var(--surface)` più shadow sempre attiva); gli altri sei erano già ri-sovrascritti da
  regole più specifiche più sotto nel file.

## Interventi eseguiti

**1. Contrasto**: `--muted:#5b6b7a` (era `#73808c`), `--ink-2:#3d4a5a` (era `#475569`).

**2. Corpo testo**: `line-height:1.42→1.5` su `body` (font-size era già 16px).

**3. Topbar mobile**: nuovo blocco `@media(max-width:768px)` che nasconde sempre `.topbar-sub`,
riduce `.topbar` a `min-height:52px`, `.brand-mark` a 28px, `.topbar-title` a 15px — **senza toccare**
il comportamento esistente `body.scrolled .topbar` (comprime a 44px allo scroll, gestito da
`header.js`), che resta intatto e continua a funzionare in aggiunta. Sotto 619px, `.page-title` 22px
e `.page-desc` 13px.

**4. Ombre**: rimossa `.card`/`.today-chip` dalla regola condivisa `--shadow-soft` (nessuna ombra,
hanno già `border`). `.radar-card.orb-card`: ombra rimossa (riposo+hover), bordo `#dbe3ec`, transition
ripulita. `.topbar`: ombra rimossa (resta `border-bottom`). `.mobile-nav`: ombra ridotta a
`0 -4px 12px rgba(28,39,60,.05)`. `.vrh-card`: ombra rimossa (ha già `border:1px solid var(--line)`).
`.btn`: nessuna ombra a riposo, mantenuta al hover.

**5. Tocco**: `touch-action:manipulation` aggiunto su `a,button,.btn,.mobile-nav a` (mancava
davvero, a differenza della copia sbagliata). `:active{transform:scale(.985)}` esteso a
`.mobile-nav a/button` e `.sheet-close`.

**6. Animazioni/glass**: rimossi `animation:orbFloat` e il relativo `@keyframes` (dead code).
Rimosso `backdrop-filter:blur(8px)` dalla topbar (era reale, non un'invenzione), sfondo portato da
`.97` a `.98` di opacità per compensare la perdita del blur.

**7. Tema scuro**: bianchi puri (`#fff`/`#ffffff`, match esatto con `var(--surface)`) tokenizzati su
`.mobile-nav`, `.navbar` (desktop), i gradienti `.radar-card.status-*`, `.status-pill` (×4),
`.today-strip .today-chip`, `.empty-state`, `.alert-card`/`.case-card`, `.btn`, `.sheet`,
`.vrh-card`, `.toast`, il gradiente di `.today-chip`, l'anello di `.status-orb`, `.home-section`,
`.home-vrh-panel`, `.status-line`. Lasciati hardcoded i bianchi-su-riempimento-saturo (`.orb-arrow`,
`.brand-mark`, `.nav-badge`, `.btn-primary`/`.btn-danger`). Palette del task in `:root` dentro
`@media(prefers-color-scheme:dark)`, verificata (vedi contrasto sotto), più override diretti (non a
token, per non rischiare il tema chiaro) per tutto ciò che qui è hardcoded e non passa da variabile:
`body`, `.topbar`, `.navbar`, `.nav-item.active`/`.mobile-nav .active`/`.page-kicker` (riusano
`var(--us)`), card name/meta/status/stats, `.home-section`/`.home-vrh-panel` e le loro righe, bordi
tinta di pill/badge/box-info/demo-banner, i gradienti `.status-orb` (adattati ai valori reali di
questo file — sono `linear-gradient(145deg,...)`, diversi da quelli radiali che avevo preventivato
prima di leggere il file vero), skeleton loader, `.sheet-handle`, `button.home-list-row:hover`, e un
override unico per `.card-mark` (base + 8 varianti tematiche).

`.home-list-row` **non** è stato forzato su `var(--surface)`: in chiaro è `background:transparent`
(le righe sono separate da un filetto, non da carte piene) — l'ho lasciato trasparente anche in
scuro, correggendo solo `border-top-color` e lo stato `:hover`, per non introdurre un aspetto a
schede che il chiaro non ha.

**8. `theme-color` sdoppiato**: sostituito il singolo meta con la coppia chiaro/scuro nelle 11
pagine reali (`viewport-fit=cover` era già presente, non toccato).

## Verifica

Stessa limitazione della sessione precedente: questo tool non naviga `file://` ("Can't interact
with browser-internal or unparseable URLs") e non ridimensiona la finestra Chrome sotto la
risoluzione desktop — **il doppio-click su `file://` non è stato verificato da me**.

Verificato con un server statico locale (`python -m http.server`) e un `<iframe>` di 375×812px
(viewport CSS realmente indipendente dalla finestra):

- **Scoperta di metodo, da tenere a mente per la FASE 2**: il sito è una PWA con service worker
  (`pwa.js`/`sw.js`) — un primo giro di test ha restituito falsi positivi (`.empty-state`, `.btn`,
  `.alert-card`, `.case-card`, `.vrh-card.orange`, alcune card a tema apparivano ancora bianche in
  scuro) causati dalla cache HTTP del browser sul tag `<link href="app.css">` dentro l'iframe, non da
  un bug reale — confermato disattivando la cache con un parametro di cache-busting sull'URL del CSS
  e rivedendo che gli stessi elementi diventano scuri correttamente. **Questo è lo stesso problema
  che il punto 10 della FASE 2 mi chiede di risolvere per il browser reale**: la cache va gestita
  esplicitamente o gli utenti continueranno a vedere l'app.css vecchio dopo un deploy.
- **Overflow orizzontale a 375px**: nessuno, su tutte le 11 pagine, chiaro e scuro.
- **Console**: nessun errore JS.
- **Scansione completa post-cache-fix, tutte le 11 pagine, tema scuro forzato**: pulite. Unico
  residuo: `.funnel-cell`/`.theme-card` su `media.html`, ma sono dentro `.funnel`/`.semafori`,
  entrambi `display:none` (markup legacy mai visibile) — falso positivo dello scanner, non un
  problema.
- **Tema chiaro**: `body` invariato (`rgb(245,247,251)` / `rgb(23,32,51)`), confermato via
  `getComputedStyle` con CSS cache-bustato.
- Screenshot dopo le modifiche, chiaro e scuro, home a 375×812:
  `docs/screenshots/home-375x812-light.png`, `docs/screenshots/home-375x812-dark.png`. Nessuno
  screenshot "prima": non l'ho fatto nella sessione sbagliata, e rifarlo ora richiederebbe uno
  stash delle modifiche già verificate — la tabella "Stato di partenza reale" sopra registra i
  valori originali.
- **Nota onesta sulla topbar mobile**: `min-height:52px` è un pavimento — l'altezza reale a runtime
  resta più alta per via del `.role-select` (dropdown ruolo, già `min-height:38px` di suo, non
  toccato: è vicino alla soglia minima di touch-target 40-44px).

## Contrasto — numeri reali

| Coppia | Sfondo | Rapporto |
|---|---|---|
| `--muted` chiaro (#5b6b7a) su `--bg`/body reale (#f5f7fb) | chiaro | **5,11:1** |
| `--ink-2` chiaro (#3d4a5a) su body reale | chiaro | **8,42:1** |
| `--muted` scuro (#8b98a5) su `--bg` scuro (#0e1319) | scuro | **6,33:1** |
| `--muted` scuro su `--surface` scuro (#171e26) | scuro | **5,70:1** |
| `--ink-2` scuro (#b8c4cf) su `--bg` scuro | scuro | **10,51:1** |
| `--ink-2` scuro su `--surface` scuro | scuro | **9,47:1** |
| `var(--us)` scuro (#b489d6) su `--bg` scuro | scuro | **6,65:1** |

Tutti ≥ 4,5:1. Nessuna correzione necessaria alla palette del task (stessi calcoli della sessione
precedente — i token in questione avevano lo stesso valore di destinazione e lo stesso `--bg`).

## Non fatto / fuori scope

- 8 varianti pastello di `.card-mark` per tema non tarate singolarmente in scuro — un override
  neutro unico le sostituisce tutte.
- `.brand-mark`, `.btn-primary`/`.btn-danger` lasciati invariati (testo bianco su riempimento
  saturo, leggibile in entrambi i temi).
- Non toccato `pilot/`, `config/`, `data/`, `input/`, `.env`, i workflow GitHub esistenti.
- Non pubblicato ancora nulla oltre a questo commit — nessun deploy Pages avviato da me in questa
  sessione oltre al push richiesto esplicitamente.

## Rischi residui

1. **Verifica `file://` mancante** — da fare manualmente.
2. Riduzione `.page-title`/`.page-desc` sotto 619px (22px/13px) è una stima, il task non dava
   numeri precisi qui.
3. Il problema di cache HTTP/PWA scoperto in verifica (vedi sopra) è reale e riguarda il browser
   reale degli utenti dopo ogni deploy, non solo il mio test — va affrontato esplicitamente nella
   FASE 2 (punto 10 del task GitHub Actions), non solo aggirato come ho fatto io per testare.
