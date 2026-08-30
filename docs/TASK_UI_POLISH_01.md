# TASK — Media Pilot: rifinitura UI (leggibilità, profondità, tocco, tema scuro)

Prompt per Claude Code.
Sito live: https://pehlivan2022.github.io/media-pilot/

## ⚠ Cartella di lavoro — controlla PRIMA di qualsiasi altra cosa

**L'unica cartella giusta è:**

```
C:\Users\frontofficedx\Desktop\media-pilot
```

**Esiste una copia vecchia e ingannevole** in
`Desktop\NIK 2026\US\________media-pilot-v21-2026-08-26\media-pilot-v21-simple`: contiene le stesse
pagine HTML e un `app.css` simile ma più vecchio (30.646 byte contro 32.976), è ferma al 26 agosto e
**non fa parte del repository**. Se lavori lì, le tue modifiche non finiscono né in git né online, e
te ne accorgi solo dopo.

Verifica di essere nel posto giusto — nella copia vecchia questi controlli falliscono tutti:

```bash
ls .git .github/workflows/publish-pages.yml pilot/run_all.py config/sources.yaml docs/
```

Se anche uno solo di questi manca, **fermati**: sei nella cartella sbagliata.

## Contesto

Dashboard di monitoraggio media politico, usata **al mattino, sul telefono, in cinque minuti, da
persone non tecniche**. Il criterio non è l'estetica: è che si capisca subito cosa conta oggi. Se un
intervento è bello ma rallenta quella lettura, non va fatto.

Questa lista viene da tre revisioni esterne, già filtrate: ho tolto ciò che era già implementato e
ciò che citava selettori inesistenti. **Tutti i selettori qui sotto esistono davvero** — verificati
in `app.css`.

## Regole

- Un solo file CSS (`app.css`), JS vanilla, **nessun framework, nessun build step, nessuna
  dipendenza**. Non proporre React/Tailwind/librerie.
- La dashboard deve continuare a funzionare **aperta da `file://` con doppio click**.
- Architettura **multipagina**: 11 pagine HTML reali (`index`, `us`, `vrh`, `media`, `case`,
  `eksperti`, `konkurenti`, `ostali`, `arhiva`, `go`, `simulator`). Non toccare `_selftest*.html`.
- Non toccare `pilot/`, `config/`, i dati.
- `prefers-reduced-motion` è già gestito globalmente: non duplicarlo, ma verifica che le tue
  aggiunte ci rientrino.

## NON rifare: è già nel codice

Verificato in `app.css`. Se lo riscrivi, stai sprecando righe:

- `-webkit-tap-highlight-color:transparent` — già su `a` e `button`
- `overscroll-behavior:none` — già su `html,body`
- `@view-transition{navigation:auto}` — è la **riga 2** del file
- `:active{transform:scale(.985)}` — già su `.radar-card.orb-card` e `.btn`
- `<meta name="theme-color">` — già in tutte le pagine (valore singolo `#7b4b9e`)
- `env(safe-area-inset-bottom)` sulla bottom nav, `viewport-fit=cover` nei meta

---

## Interventi, in quest'ordine

### 1. Contrasto dei grigi

Misurato: `--muted:#73808c` su `--bg:#f3f5f7` dà **3,70:1** — sotto il 4,5:1 richiesto per il testo
piccolo. Al sole e per lettori non giovani sparisce.

```css
--muted:#5b6b7a;   /* era #73808c → 5,0:1 */
--ink-2:#3d4a5a;   /* era #475569 */
```

`#5b6b7a` è scelto per passare AA **mantenendo** la distinzione dal testo principale: non scurirlo
oltre, o il secondario smette di leggersi come secondario.

### 2. Corpo del testo

`body` dichiara `font-size:15px; line-height:1.42`. Portalo a:

```css
font-size:16px; line-height:1.5;
```

**Mettilo su `body`, non su `:root`**: la regola su `:root` verrebbe sovrascritta da quella
esistente su `body` e non avrebbe alcun effetto.

Dopo la modifica **controlla che le card non vadano in overflow** a 375px: la scala tipografica
(`.t-12`…`.t-40`) è in px assoluti e non si muove, ma il testo di corpo sì.

### 3. Topbar più bassa su mobile

Oggi: `min-height:60px`, `padding:10px 14px`, e `.topbar-sub` visibile finché non scrolli. Sommata a
`.page-title` + `.page-desc`, il primo dato utile inizia **sotto i 130px**, cioè oltre il primo
sesto di uno schermo da 812px.

Su mobile: `.topbar-sub` nascosto **sempre** (non solo dopo lo scroll), `min-height:52px`,
`.brand-mark` a 28px, `.topbar-title` a 15px. Riduci anche `.page-title` e `.page-desc` sotto i
619px. Non toccare il comportamento desktop.

### 4. Ombre: solo su ciò che fluttua davvero

Quattro livelli d'ombra su fondo chiaro sono troppi. **Attenzione**: `--shadow-card` è applicata da
una regola condivisa fra `.topbar, .navbar, .mobile-nav, .card, .vrh-card, .sheet, .btn,
.today-chip` — vanno separate, non modificate in blocco.

Nuova regola:

| elemento | trattamento |
|---|---|
| `.card`, `.vrh-card`, `.radar-card.orb-card` | **nessuna ombra**, `border:1px solid #dbe3ec` |
| `.sheet` | ombra piena: sta davvero sopra |
| `.mobile-nav` | ombra sottile verso l'alto: `0 -4px 12px rgba(28,39,60,.05)` |
| `.topbar` | nessuna ombra, basta il `border-bottom` |
| `.btn`, `.today-chip` | nessuna ombra a riposo |

Togli anche le `transition` su `box-shadow` rimaste orfane.

### 5. Tocco

Aggiungi (non c'è): `touch-action:manipulation` su `button, a, .btn, .mobile-nav a` — elimina il
ritardo del doppio tap.

Estendi il feedback `:active` già esistente anche alle voci della bottom nav e dello sheet, con gli
stessi valori usati oggi (`scale(.985)`), per coerenza.

### 6. Via le animazioni decorative

- `animation:orbFloat 2.6s ease-in-out infinite` — **attiva**, va rimossa. È un movimento continuo
  su una pagina che si guarda cinque minuti: consuma batteria e distrae. Rimuovi la dichiarazione,
  **lascia l'elemento** al suo posto, statico.
- `backdrop-filter:blur(8px)` su `.topbar` — unico glass del progetto. Rimuovilo e porta lo sfondo a
  `rgba(255,255,255,.98)`. Su Android di fascia media il blur combinato allo scroll costa frame, e
  qui non aggiunge nulla.

### 7. Tema scuro

**Prima di scrivere la palette, fai questo passo o il tema scuro non funzionerà.**

Nel CSS ci sono **53 occorrenze di bianco hardcoded** (`#fff` / `rgba(255,255,255,…)`) su almeno 22
selettori: `.topbar`, `.navbar`, `.mobile-nav`, `.sheet`, `.btn`, `.today-chip`, `.vrh-card`,
`.home-section`, `.home-vrh-panel`, `.case-card`, `.alert-card`, `.empty-state`, `.status-line`,
`.toast`, i `.status-*-pill`, i `.theme-*-card-mark` e `.theme-*-card-theme-pill`.

Ridefinire i token di `:root` **non li tocca**: resterebbero bianchi su fondo scuro.

Quindi, nell'ordine:

1. **Converti i bianchi hardcoded in token** (`var(--surface)` dove è una superficie, `var(--bg)`
   dove è il fondo). Fallo come passo separato e verifica che il tema chiaro sia **identico a
   prima** — è un refactor a resa zero, se cambia qualcosa hai sbagliato una sostituzione. Lascia
   hardcoded solo i bianchi che sono davvero bianco puro anche di notte (es. testo su pillola
   colorata piena).
2. **Poi** aggiungi il blocco scuro. Usa `@media (prefers-color-scheme: dark)`, **niente JavaScript
   e niente interruttore** in questo giro: se poi servirà un toggle manuale si aggiunge sopra senza
   rifare la palette.

Palette di partenza (verifica ogni valore ≥4,5:1 e correggi se non passa — non fidarti):

```css
@media (prefers-color-scheme: dark){
  :root{
    --bg:#0e1319; --surface:#171e26; --surface-2:#1f2933; --surface-3:#27313c;
    --line:#2b3642; --line-strong:#3a4754;
    --ink:#e6edf3; --ink-2:#b8c4cf; --muted:#8b98a5;
    --ok:#3fba7a; --ok-bg:#102a1c;
    --warn:#e8a13c; --warn-bg:#2a2110;
    --crit:#e85c5c; --crit-bg:#2a1515;
    --info:#64a5e8; --info-bg:#122536;
    --us:#b489d6; --us-bg:#2a1f33;
  }
}
```

Il viola del partito va schiarito: `#7b4b9e` su fondo scuro non ha contrasto sufficiente.

Gestisci anche i gradienti degli `.status-orb` (`.status-red`, `.status-orange`, `.status-blue`,
`.status-green`, `.status-grey`), che sono colori pieni e su fondo scuro risultano troppo accesi.

### 8. `theme-color` sdoppiato

Nelle 11 pagine, sostituisci il meta singolo con la coppia:

```html
<meta name="theme-color" content="#7b4b9e" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#171e26" media="(prefers-color-scheme: dark)">
```

Così la barra di stato della PWA installata segue il tema invece di restare viola sul nero.

---

## Verifica

Non dichiarare fatto senza aver visto il risultato.

1. **A 375×812**, tema chiaro e tema scuro: nessuno scroll orizzontale
   (`document.documentElement.scrollWidth <= window.innerWidth`), nessun errore in console, testo
   non troncato nelle card.
2. **Screenshot prima/dopo** della home a 375×812 nei due temi.
3. **Contrasto**: calcola e riporta il rapporto reale di `--muted` e `--ink-2` sui rispettivi
   sfondi, chiaro e scuro. Numeri, non "sembra a posto".
4. **Doppio click su `index.html`** (`file://`): deve funzionare come prima.
5. Il tema chiaro dopo il punto 7.1 deve essere **pixel-identico** a prima del refactor.

Se lo strumento di automazione non riesce a emulare 375×812 o a navigare `file://`, **dimmelo**
invece di dichiarare verificato ciò che non hai visto.

## Consegna

Report in `docs/TASK_UI_POLISH_01_RESULTS.md`: cosa hai cambiato punto per punto, i numeri di
contrasto misurati, gli screenshot, cosa **non** hai fatto e perché, rischi residui.

Poi fermati: non pubblicare su GitHub Pages, te lo chiedo io dopo aver guardato.

## Se qualcosa non torna

Se trovi che un punto di questo task è sbagliato rispetto al codice reale — un selettore che non
esiste, un valore diverso da quello che ho scritto — **fermati e dimmelo** invece di adattare il
codice al testo. Le tre revisioni da cui viene questa lista contenevano già diversi selettori
inventati: non escludo di averne lasciato passare uno.
