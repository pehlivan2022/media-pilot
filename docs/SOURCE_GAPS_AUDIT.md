# SOURCE GAPS AUDIT

Date: 2026-08-29. `TASK_EXTERNAL_SOURCES_AND_REAL_DASHBOARD_02.md` §4. Basato su dati gia' misurati
(`docs/SOURCE_AUDIT.csv`, `config/sources.yaml`, `docs/FINAL_PROJECT_STATUS.md`,
`docs/TASK_BETA_03_RESULTS.md`) — nessun nuovo fetch live dove il dato esistente e' gia' affidabile, per
non duplicare il lavoro di `pilot/sources.py`. Colonna "possible external helper" fa riferimento
all'audit in `docs/EXTERNAL_SCRAPER_AUDIT_V2.md`: **verdetto REJECT su tutti e 6 i candidati**, quindi
nessuno dei gap sotto ha un aiuto esterno reale disponibile da quell'elenco — dichiarato esplicitamente
riga per riga invece di lasciarlo implicito.

**Regola rispettata**: Banjaluka24 (`BL_IJ3_006`) NON compare come problema — contaminazione gia' corretta
in `TASK_BETA_03_RESULTS.md` D0.1 (71,4%→0%), nessuna nuova regressione misurata.

---

## Fonti con gap reale

| source_id | nome | problema | RSS? | storico sufficiente? | parser affidabile? | frequenza sufficiente? | articoli persi? | discovery gap? | categoria | possible external helper |
|---|---|---|---|---|---|---|---|---|---|---|
| `RS_IJ_018` | InfoBijeljina | `window_actual_days: 0` — il peggiore del registry (`FINAL_PROJECT_STATUS.md`) | No (`html_home_links`) | **No** (0 giorni) | Debole (fallback link-homepage, non sitemap/RSS) | No | Probabile si | Si | `NO_RSS` + `SHORT_HISTORY` + `DISCOVERY_GAP` | Nessuno dei 6 (nessuna copertura BiH/RS in alcun candidato) |
| `RS_ENT_001` | RTRS | Storico bloccato a 2 giorni; RSS ad alto volume (100 item/7d) satura la finestra | Si, ma finestra corta | **No** (2gg, gia' auditato: nessun sitemap, Wayback CDX 0 item nuovi — `TASK_BETA_03_RESULTS.md` D0.2) | Si (RSS diretto) | Si (alto volume) | Si, oltre le 100 entry piu' recenti | No (il problema e' profondita' storica, non discovery) | `SHORT_HISTORY` | Nessuno — verificato esplicitamente in questo giro (vedi nota RTRS sotto) |
| `SRC_009` | N1 BiH | `window_actual_days: 2`, RSS alto volume (50/7d) | Si | No (2gg) | Si | Si | Probabile, oltre la finestra RSS | No | `SHORT_HISTORY` | Nessuno |
| `FBIH_001` | Klix.ba | `window_actual_days: 2`, RSS alto volume (30/7d) | Si | No (2gg) | Si | Si | Probabile, oltre la finestra RSS | No | `SHORT_HISTORY` | Nessuno |
| `BL_IJ3_003` | Glas Srpske | Nessun feed RSS, solo sitemap+html; `items_7d_at_audit: 3`, `window: 2` | **No** | No (2gg) | Debole (estrazione HTML via sitemap, non feed strutturato) | No | Probabile | Si (sitemap limitato) | `NO_RSS` + `SHORT_HISTORY` + `BAD_EXTRACTION` (rischio) | Nessuno |
| `RS_IJ_001` | BN / RTV BN | Nessun feed RSS; `items_7d: 3`, `window: 4` | **No** | Parziale (4gg) | Debole (sitemap+html) | No | Probabile | Si | `NO_RSS` + `LOW_FREQUENCY` | Nessuno |
| `RS_IJ_012` | Glas Regije | `window_actual_days: 3` nonostante RSS attivo (10/7d) | Si | No (3gg) | Si | Parziale | Probabile | No | `SHORT_HISTORY` | Nessuno |
| `RS_IJ_013` | Dobojski.info | Nessun sitemap stabile, solo Wayback CDX; `items_7d: 2`, `window: 2` | **No** | No (2gg, solo 5 capture totali nella finestra — `TASK_BETA_03_RESULTS.md`) | Debole (dipende da Wayback, non dal sito live) | No | Si | Si | `NO_RSS` + `SHORT_HISTORY` + `DISCOVERY_GAP` | Nessuno |
| `ECO_001` | Capital.ba | Sito live BLOCKED (HTTP 403), reale solo via Wayback CDX; query CDX instabile con filtro data stretto | No (nessun feed) | Si (9gg via Wayback) | Debole (dipende da Wayback + query instabile) | Parziale | Possibile | Si (accesso diretto bloccato) | `INTERMITTENT_FAILURE` (accesso diretto) | Nessuno |
| `BIH_ELEC_003` | Transparency International BiH | `items_7d: 2`, `window: 6` — volume molto basso | No (sitemap+html) | Parziale | Debole | **No** | Possibile | Parziale | `LOW_FREQUENCY` | Nessuno |
| `BIH_ELEC_002` | Koalicija Pod lupom | `items_7d: 3`, `window: 5` — volume basso | Si (RSS) | Parziale | Si | **No** | Possibile | No | `LOW_FREQUENCY` | Nessuno |

## Fonti senza gap significativo (non incluse sopra)

`POL_RS_001` (SNSD), `RS_ENT_002` (ATV, storico esteso a 7gg dopo D0.2), `BL_IJ3_001` (Srpskainfo, 9gg),
`BL_IJ3_002` (Nezavisne, 27gg — il migliore del registry), `BL_IJ3_007` (BL Portal, 7gg), `RS_IJ_014`
(RTV Doboj, 7gg) — RSS attivo, volume e finestra ragionevoli, nessuna azione richiesta.

---

## Nota RTRS — verifica esplicita richiesta dalla task (§4)

La task chiede di verificare se un provider esterno "aggiunge realmente storico/copertura" per RTRS
prima di dargli credito, non di assumerlo. Nessuno dei 6 candidati auditati offre un percorso diverso da
quello gia' provato (RSS diretto + Wayback CDX, entrambi gia' testati in `TASK_BETA_03_RESULTS.md` D0.2 —
Wayback CDX ha dato **0 item nuovi** nella finestra). `open-news`/`news-please`/`RSS-Bridge` userebbero
lo stesso RSS pubblico di RTRS gia' in uso o richiederebbero uno scraping HTML equivalente a quello che
il nostro `collect.py` gia' fa — **nessun valore incrementale reale confermato**, coerente con l'esito
atteso dalla task per questo caso specifico.

## Categorie usate

`NO_RSS` (5 fonti: RS_IJ_018, BL_IJ3_003, RS_IJ_001, RS_IJ_013, e Capital.ba priva di feed pur avendo
un metodo alternativo), `SHORT_HISTORY` (7 fonti: RTRS, N1, Klix, Glas Srpske, Glas Regije, Dobojski.info,
InfoBijeljina), `BAD_EXTRACTION` (rischio dichiarato su Glas Srpske, non misurato come difetto attivo),
`DISCOVERY_GAP` (3: InfoBijeljina, Dobojski.info, Capital.ba — dipendono da un metodo di scoperta debole
o indiretto), `INTERMITTENT_FAILURE` (1: Capital.ba, bloccata in diretta), `LOW_FREQUENCY` (2: Koalicija
Pod lupom, Transparency International BiH). Nessuna categoria `OTHER` necessaria.

## Conclusione

10 fonti su 18 hanno un gap dichiarato, nessuna con un aiuto esterno reale disponibile tra i 6 candidati
auditati in questo giro (`docs/EXTERNAL_SCRAPER_AUDIT_V2.md`, REJECT su tutti). I gap restano dichiarati,
non forzati: la maggior parte (7/10) e' `SHORT_HISTORY` — un limite di profondita' temporale che richiede
un archivio storico diverso da RSS/sitemap/Wayback per queste testate specifiche (gia' concluso per RTRS
in `TASK_BETA_03_RESULTS.md`), non risolvibile aggiungendo un provider di discovery generico.
