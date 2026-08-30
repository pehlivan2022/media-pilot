# RFC — Media Pilot: come migliorare la dashboard (richiesta di seconda opinione)

**Sito live, guardalo prima di rispondere:** https://pehlivan2022.github.io/media-pilot/

Aprilo **sul telefono** o con le devtools in modalità mobile (375×812): è lì che viene usato.
Se il tuo strumento non può navigare, dimmelo e ti incollo il CSS.

---

## 1. A cosa serve questa pagina

È il **radar mediatico-politico** del partito Ujedinjena Srpska, in vista delle elezioni 2026 in
Republika Srpska / Bosnia Erzegovina. Non è un prodotto commerciale e non deve vendere niente.

**Chi la usa:** una decina di persone dello staff di partito e la dirigenza. Non sono utenti
tecnici.

**Come la usa:** al mattino, sul telefono, in cinque minuti, spesso in movimento. La domanda a cui
la pagina deve rispondere è: *"cosa è successo nella notte che mi riguarda, e cosa devo guardare
oggi?"*. Poi, più raramente, qualcuno la apre su desktop per scendere nel dettaglio.

**Cosa mostra:** una rassegna di ~1.000 articoli raccolti ogni notte da 33 fonti locali, raggruppati
in ~600 cluster; le entità politiche in crescita ("trending", con momentum in %); i "signal" da
rivedere; le sezioni per il vertice del partito, i media, i concorrenti, i territori, l'archivio.
Lingua dell'interfaccia: **serbo latino** (`lang="sr-Latn"`).

**Il criterio di successo non è l'estetica**: è che una persona non tecnica, in cinque minuti sul
telefono, capisca cosa conta oggi. Se una proposta è bella ma rallenta quella lettura, non la
voglio.

---

## 2. Cosa c'è già (fatti, non impressioni)

Prima di proporre, sappi cosa esiste — così non mi proponi cose già fatte.

**Architettura**
- **11 pagine HTML separate**, non una SPA. Niente router, niente framework, niente build step.
  JavaScript vanilla, un file CSS unico (`app.css`, ~32 KB).
- Deve continuare a funzionare **anche aperta da `file://` con doppio click**, oltre che online.
- È una **PWA installabile** (manifest + service worker), quindi da telefono può girare a schermo
  intero senza barra del browser.

**Sistema visivo attuale**
- **Solo tema chiaro.** Nessun supporto per `prefers-color-scheme`: zero occorrenze nel CSS.
- Token colore: `--bg:#f3f5f7`, `--surface:#fff`, testo `--ink:#18212b`, secondario `#475569`,
  muted `#73808c`. Semantici: ok `#168552`, warn `#a86a00`, crit `#c73535`, info `#2869a8`.
  Colore del partito: viola `--us:#7b4b9e`.
- Raggi: 8 / 12 / 18 px. Spaziatura: scala 4-8-12-16-24-32.
- **Quattro token d'ombra** già definiti: `--shadow-soft`, `--shadow-card`, `--shadow-card-hover`,
  `--shadow-orb` (quest'ultima con ombre interne, per l'elemento "orb" della home).
- **Glass: uno solo** — `backdrop-filter:blur(8px)` sulla topbar, che è `sticky` e si comprime da
  60px a 44px allo scroll.
- Animazioni: transizioni 0.15–0.25s su `transform`/`box-shadow` sulle card, un `orbFloat` di 2.6s,
  uno skeleton di caricamento. `prefers-reduced-motion` è già rispettato.
- Tipografia: `font-size:15px`, `line-height:1.42`, scala 12/14/16/20/28/40 con pesi fino a 800.
  **Nota:** la font-family dichiara `Inter` per prima ma **nessun webfont viene caricato** (niente
  `@font-face`, niente Google Fonts), quindi nella pratica quasi tutti vedono il font di sistema.
  Se pensi che valga la pena caricare Inter davvero, dimmelo con i costi.
- Mobile: **bottom tab bar a 5 voci** fissa, con `env(safe-area-inset-bottom)`; menu completo in un
  **bottom sheet**; target touch da 62px. Desktop: sidebar da 196px.

---

## 3. Cosa ti chiedo

Rispondi **in quest'ordine**, e sii concreto: CSS vero, non aggettivi.

1. **Leggibilità e gerarchia.** Guardando la home su mobile: cosa legge per primo l'occhio, e cosa
   *dovrebbe* leggere per primo dato lo scopo al §1? Se non coincidono, come lo sistemo — con la
   tipografia, con lo spazio, o togliendo roba? Dimmi in particolare se 15px/1.42 e i grigi
   `#475569`/`#73808c` reggono su uno schermo al sole, per lettori non giovani.

2. **Cosa togliere.** Prima di aggiungere: c'è qualcosa che occupa spazio e non serve alla domanda
   delle cinque del mattino? Preferisco una risposta che toglie a una che aggiunge.

3. **Profondità: ombre o bordi?** Ho quattro livelli d'ombra su fondo chiaro. È troppo? Su mobile
   conviene passare a superfici piatte separate da linee, e tenere l'ombra solo per gli elementi
   che stanno davvero sopra (sheet, tab bar)? Dammi i valori che consigli.

4. **Glass.** Oggi c'è solo sulla topbar. Vale la pena estenderlo (tab bar, sheet) o è un effetto
   che su Android di fascia media costa frame e basta? Se sì dove, con quali fallback, e come lo
   verifico.

5. **Animazioni.** Quali movimenti aiutano a capire *dove sono finito* (transizioni di pagina,
   apertura dello sheet, aggiornamento dei dati) e quali sono solo decorazione da togliere? Durate
   e curve precise. Ricorda che le pagine sono **documenti separati**: le transizioni tra pagine
   devono funzionare tra documenti, non dentro una SPA.

6. **Tema scuro.** Oggi non esiste. Per un'app aperta la mattina presto ha senso aggiungerlo? Se sì,
   dammi la palette scura completa a partire dai token del §2, e dimmi come gestire i colori
   semantici (ok/warn/crit) e il viola del partito, che su fondo scuro perdono contrasto.

7. **Sensazione "app" vera.** Cosa manca perché, installata sul telefono, non sembri un sito dentro
   un guscio? Elenca le due o tre cose che fanno più differenza, non dieci.

8. **Priorità.** Chiudi con un elenco ordinato: cosa faccio per primo, e per ognuna quanto costa
   (righe di CSS, minuti) e cosa ci guadagno. Se una proposta richiede un framework, un build step
   o una libreria, **dimmelo esplicitamente** perché in quel caso la scarto.

---

## 4. Vincoli, così non sprechi la risposta

- Niente framework, niente build step, niente npm. CSS e JS scritti a mano.
- Deve continuare a funzionare aperta da `file://`.
- Nessuna dipendenza esterna a runtime, tranne eventualmente un webfont — e in quel caso motivalo.
- Multipagina: non proporre di riscriverla come SPA.
- L'accessibilità di base non si tocca: `prefers-reduced-motion`, focus visibile, contrasto.
- Non inventare com'è fatta la pagina: se un dettaglio non lo trovi nel §2 e non riesci a vederlo
  dal sito, **chiedimelo** invece di supporre.

---

## 5. Cosa ho già escluso

Non ripropormi queste, sono decisioni prese:

- Riscrittura in React/Vue/Svelte, o SPA con router.
- Tailwind o qualsiasi framework CSS.
- Rimozione della bottom tab bar mobile: c'è ed è la navigazione principale.
- Rendere la pagina pubblica/indicizzabile: è materiale interno, ha `noindex`.
- Grafici complessi o dataviz elaborate: i dati cambiano una volta al giorno, non servono
  visualizzazioni in tempo reale.
