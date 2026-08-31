# TASK FASE 3 — risultati

**Scritto:** 2026-08-31/09-01, sessione che ha eseguito i task del predecessore
`docs/TASK_FASE3_NEXT.md`.

---

## ORDINE punto 1 — esito del run `33355679965`

Il run non era "ancora in corso", era **fallito**. Il passo "Run pipeline" ha impiegato
**44m43s** (2683s, non i ~7 min osservati a metà corsa), poi "Commit dashboard outputs" ha
fallito con `! [rejected] master -> master (fetch first)`: master si era mosso (commit TASK F)
durante i 45 minuti di run, il push finale non era un fast-forward. L'intero output di quel
run (`rassegna.json`, `signals.json`, `trending.json`, `pipeline_health.json`) è andato perso,
mai pubblicato. `data/raw` ed `errors.jsonl` invece si sono salvati (push separato, riuscito).

**Fix:** `git pull --rebase` prima di entrambi i push in `daily-pipeline.yml` (commit `83a9a3e`).

---

## TASK F — stato: parzialmente completato, criteri di accettazione NON raggiunti

### Cosa era già fatto all'inizio di questa sessione

Commit `8adf6ae` (di una sessione precedente) implementava già la variante A2 descritta nel task:
`exclude_canonical` popolato da `data/raw/*.jsonl` e passato lungo
`collect()` → `collect_supplemental_history()` → `collect_from_sitemap_backfill()` /
`collect_from_wayback_cdx()`. Verificato leggendo il codice: il filtro si applica **prima** del
cap `MAX_BACKFILL_URLS`, quindi riduce davvero il numero di fetch (non solo li ridirige). 27/27
test verdi, incluso `test_19` nuovo per questo filtro.

### Due bug nuovi trovati e corretti in questa sessione

1. **`UnicodeEncodeError` non gestito** (`pilot/util.py`): un URL da sitemap con un carattere
   non-ASCII grezzo (es. `₂`) mandava in crash `http.client.putrequest` (ascii-only), non
   catturato dal blocco `except` esistente (`URLError`/`TimeoutError`/`ConnectionError` — non
   `UnicodeEncodeError`, che è una `ValueError`). Uccideva l'intera pipeline a metà (fonte 22/33)
   invece di essere loggato come errore di una fonte sola. **Fix:** `quote(url, safe=...)` prima
   della request (commit `128713a`).
2. **Fetch sequenziali** (`pilot/collect.py`): nessuna concorrenza da nessuna parte in `collect()`.
   `duration_sec` ≈ `items_fetched × 1.87s/item` — quasi tutto il tempo di run è I/O di rete
   bloccante, un URL alla volta. Provata parallelizzazione con `ThreadPoolExecutor`
   (`BACKFILL_FETCH_WORKERS=8`, stdlib) sui due loop a volume più alto (sitemap e wayback
   backfill, fino a 100 fetch ciascuno). **Risultato misto** — vedi tabella sotto: `duration_sec`
   è sceso ma `items_written` è crollato e i fallimenti fonte sono aumentati, probabile
   rate-limiting/timeout lato fonti sotto carico concorrente. Non ottimizzato oltre
   (`BACKFILL_FETCH_WORKERS` andrebbe abbassato e/o servirebbe backoff sui 429/503) —
   **ceiling noto, non risolto in questa sessione.**

### Numeri: tre run Actions reali, in ordine

| Run | commit | esito | duration_sec | items_fetched | items_written | sources_failed | skip (window≥7) |
|---|---|---|---|---|---|---|---|
| `33355679965` | `923cde1` (A1 soltanto) | fallito al push finale | 2683 (44m43s) | — (mai pubblicato) | — | — | 6/25 (baseline pre-F) |
| `33439182040` | `83a9a3e` (+A2, no fix unicode) | **crash** a fonte 22/33 | — | — | — | — | — |
| `33442356029` | `128713a` (+fix unicode) | **successo**, primo run pulito con A2 | 2338.9 | 1250 | 1055 | 15 | 9/25 |
| `33448822718` | `9d4f2a1` (+concorrenza) | successo | 1720.2 | 1155 | **340** | **17** | 9/25 |

### Criteri di accettazione del task originale — verdetto

- `duration_sec` < 600 → **non raggiunto** (migliore risultato: 1720.2s, 2.9× il target)
- fonti che saltano il supplemento ≥ 20/25 → **non raggiunto** (9/25, invariato tra gli ultimi
  due run)
- nessun articolo perso → **non verificato positivamente**: l'ultimo run (con concorrenza) ha
  scritto 340 item contro i 1055 del run precedente, con più fonti fallite. Prima di riusare
  `BACKFILL_FETCH_WORKERS=8` in produzione andrebbe capito se è perdita reale o fonti che quel
  giorno erano più lente/instabili.
- `python -m pilot.test_pipeline` verde con test su `exclude_canonical` → **fatto** (27/27,
  `test_19`)

### Perché il criterio ≥20/25 potrebbe non essere raggiungibile in un solo run

A2 fa avanzare `window_actual_days` di un giorno o poco più per fonte per run (osservato: quasi
tutte le fonti RSS sono salite di 1 tra il run pre-F e il primo run post-A2). Con la finestra a 7
giorni, le fonti più indietro richiedono più run consecutivi per raggiungere la soglia — non è un
difetto del fix, è come A2 è stato progettato (converge nel tempo, non subito). Con il cron ancora
spento (TASK B), questa convergenza avanza solo con run manuali.

### Non ancora deciso

- Se abbassare `BACKFILL_FETCH_WORKERS` (es. a 3-4) o aggiungere retry/backoff sui 429/503 per
  recuperare il calo di `items_written` mantenendo un po' di velocità.
- Se la strada giusta per `duration_sec` < 600 sia continuare a spingere sulla concorrenza, o
  ridurre `MAX_BACKFILL_URLS`, o dividere le fonti su più run schedulati (es. metà fonti al
  mattino, metà alla sera) invece di un unico crawl completo.
- TASK H (riaccensione cron) resta bloccato: nessuno dei tre run ha rispettato il target
  `duration_sec` < 600.

---

## TASK G — vedi resto di questo file quando completato in questa sessione.
