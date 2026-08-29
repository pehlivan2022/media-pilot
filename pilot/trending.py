"""§D1 TASK_BETA_03 — Trending Engine PER ENTITA', non per cluster: un'entita' puo' "salire" anche
su articoli mai finiti nello stesso cluster (il vecchio `signal_score` dipende troppo dai cluster,
vedi BETA_RESULTS.md). Legge data/scored_items.jsonl (post score.run(): `modules`/`cluster_id`/
`is_relevant` gia' calcolati, nessun ricalcolo qui), scrive data/trending_entities.jsonl — un
record per entita' del registry (config/entities.yaml, 55 voci), MAI un'entita' nuova inventata.

Zero invenzione: `baseline_7d` resta `None` se la finestra storica per QUELL'entita' e' troppo
sottile (meno di MIN_BUCKETS_FOR_BASELINE bucket da 4h popolati), `baseline_30d` resta sempre
`None` in questo task — nessuna fonte ha 30gg di copertura piena su tutte le entita' (vedi C4/D0.2
in TASK_BETA_03_RESULTS.md), quindi non e' una misura, sarebbe un'invenzione.

NOTA architetturale su assets/data/trending.json (aggiornata in MEDIA_PILOT_FINAL_HANDOFF.md §15,
dopo la decisione presa in TASK_BETA_03_RESULTS.md §D1): tracciato `radar.js` prima di scrivere
l'adapter. `RadarEngine.trending()` NON legge `trending.json` come "lista di trending gia'
calcolati" — lo tratta come altri item da versare nello stesso pool di `rassegna.json` (schema
articolo: title/menu/date/modules), e ricalcola da solo la sua nozione di "trending" (ripetizione
di modulo fra articoli + source jump, `radar.js` righe 42-150). Il §15 dell'handoff finale chiede
esplicitamente uno schema DIVERSO, per entita' (entity_id/mentions/momentum/evidence, non
title/menu) — non piu' un tentativo di adattarsi allo schema-articolo (che avrebbe richiesto
inventare quei campi). Scritto cosi': `export_trending_json()` sovrascrive `trending.json` con lo
schema nuovo dell'handoff. Effetto collaterale dichiarato, non nascosto: le righe non hanno
`menu`, quindi `RadarEngine.rassegna()`/`trending()` (che filtrano su `menu`) le ignorano
silenziosamente — non le rompono, ma non le "vedono" nel funnel esistente. Collegare questi dati a
un tab Trending vero e proprio e' lavoro di frontend (§J), esplicitamente fuori scope qui
("no frontend rewrite")."""
import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from pilot.entities import load_entities_yaml
from pilot.score import load_sources_by_id

ROOT = Path(__file__).resolve().parent.parent
SCORED_ITEMS_JSONL = ROOT / "data" / "scored_items.jsonl"
TRENDING_JSONL = ROOT / "data" / "trending_entities.jsonl"
TRENDING_ASSET_JSON = ROOT / "assets" / "data" / "trending.json"
MAX_EVIDENCE_URLS = 10

BASELINE_WINDOW_DAYS = 7
MIN_BUCKETS_FOR_BASELINE = 2 * 6  # almeno 2 giorni di bucket da 4h popolati prima di fidarsi di una mediana


def _dt(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_scored_items():
    items = []
    with open(SCORED_ITEMS_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def _bucket_4h(d):
    b = d.replace(minute=0, second=0, microsecond=0)
    return b.replace(hour=(b.hour // 4) * 4)


def _top_events(mentions, limit=3):
    """I cluster con piu' mention nella finestra, un evento rappresentativo (il piu' recente
    membro) per ognuno — cosi' ogni riga di trending porta evidence reale, non solo un conteggio."""
    by_cluster = defaultdict(list)
    for d, it in mentions:
        by_cluster[it.get("cluster_id")].append((d, it))
    ranked = sorted(by_cluster.items(), key=lambda kv: -len(kv[1]))[:limit]
    out = []
    for cluster_id, members in ranked:
        members.sort(key=lambda pair: pair[0], reverse=True)
        d, it = members[0]
        out.append({
            "cluster_id": cluster_id, "title": it.get("title"), "url": it.get("url"),
            "source_id": it.get("source_id"), "published_at": it.get("published_at"),
            "n_items": len(members),
        })
    return out


def compute_trending(items, sources_by_id, entities):
    relevant = [it for it in items if it.get("is_relevant") and it.get("published_at") and _dt(it["published_at"])]
    all_dts = sorted(_dt(it["published_at"]) for it in relevant)
    if not all_dts:
        return []
    now = all_dts[-1]  # stessa convenzione di score.py: l'ultimo istante osservato nel corpus
    owner_by_source = {sid: (s.get("owner_group") or sid) for sid, s in sources_by_id.items()}

    # se il CORPUS non copre nemmeno BASELINE_WINDOW_DAYS giorni civili, i bucket prima dell'inizio
    # della raccolta sarebbero zero per mancanza di dati, non perche' l'entita' tace: la mediana
    # sottostimerebbe il ritmo normale. Stesso principio di baseline_incomplete in score.py (B0),
    # qui applicato PRIMA di calcolare qualunque baseline_7d, non entita' per entita'.
    corpus_days = len({d.date() for d in all_dts})
    baseline_window_ok = corpus_days >= BASELINE_WINDOW_DAYS

    total_24h = sum(1 for it in relevant if (now - _dt(it["published_at"])) <= timedelta(hours=24))

    by_entity = defaultdict(list)
    for it in relevant:
        dt_i = _dt(it["published_at"])
        for key in it.get("modules") or []:
            by_entity[key].append((dt_i, it))

    rows = []
    for ent in entities:
        key = ent["key"]
        mentions = sorted(by_entity.get(key, []), key=lambda pair: pair[0])

        def _window(hours):
            return [(d, it) for d, it in mentions if (now - d) <= timedelta(hours=hours)]

        def _unique_events(window):
            return len({it.get("cluster_id") for _, it in window if it.get("cluster_id")})

        def _unique_sources(window):
            return len({owner_by_source.get(it["source_id"], it["source_id"]) for _, it in window})

        w1h, w4h, w24h = _window(1), _window(4), _window(24)

        # baseline_7d: mediana di mention/bucket-4h sugli ultimi BASELINE_WINDOW_DAYS, bucket
        # VUOTI inclusi (stesso principio di velocity_baseline_4h in score.py, B0: altrimenti si
        # misura "quanto parla quando parla", non il ritmo normale). None se la finestra e' troppo
        # sottile per quell'entita' — zero invenzione, non si stima su pochi bucket.
        window_start = now - timedelta(days=BASELINE_WINDOW_DAYS)
        baseline_7d = None
        if baseline_window_ok and any(window_start <= d <= now for d, _ in mentions):
            bucket_counts = {}
            cur = _bucket_4h(window_start)
            last = _bucket_4h(now)
            while cur <= last:
                bucket_counts[cur] = 0
                cur += timedelta(hours=4)
            for d, _ in mentions:
                if window_start <= d <= now:
                    bucket_counts[_bucket_4h(d)] += 1
            if len(bucket_counts) >= MIN_BUCKETS_FOR_BASELINE:
                counts_sorted = sorted(bucket_counts.values())
                # B0 in score.py insegna: una mediana 0 (entita' citata raramente, la maggior parte
                # dei bucket da 4h e' vuota) non vuol dire "nessun ritmo normale", vuol dire che il
                # ritmo normale e' il minimo misurabile - clampato a 1 come velocity_baseline_4h,
                # altrimenti un `if baseline_7d` piu' sotto tratterebbe 0 come "non misurato" e un
                # burst reale finirebbe con acceleration=None invece di un numero alto.
                baseline_7d = max(counts_sorted[len(counts_sorted) // 2], 1)

        acceleration = round(len(w4h) / baseline_7d, 3) if baseline_7d else None

        # MEDIA_PILOT_FINAL_HANDOFF.md §14/§15: "momentum" e' un concetto distinto da acceleration
        # (che confronta il bucket da 4h corrente col ritmo normale a grana fine) - qui si confronta
        # mentions_24h con una baseline GIORNALIERA (media di mention/giorno sugli ultimi 7gg,
        # giorni senza mention inclusi, stesso principio di baseline_7d sopra), come "+153% vs
        # normale" invece di un rapporto assoluto. Riprodotto sull'esempio numerico dell'handoff
        # (12 mention, baseline 3.4 -> momentum 2.53 = (12-3.4)/3.4): verificato che torna.
        baseline_daily_7d = None
        if baseline_window_ok and any(window_start <= d <= now for d, _ in mentions):
            days_in_window = {(window_start + timedelta(days=i)).date() for i in range(BASELINE_WINDOW_DAYS + 1)}
            per_day = {d0: 0 for d0 in days_in_window}
            for d, _ in mentions:
                if window_start <= d <= now:
                    per_day[d.date()] = per_day.get(d.date(), 0) + 1
            if per_day:
                baseline_daily_7d = round(sum(per_day.values()) / len(per_day), 3)
        momentum = round((len(w24h) - baseline_daily_7d) / baseline_daily_7d, 3) if baseline_daily_7d else None

        top_events = _top_events(w24h or mentions[-5:])
        evidence_urls = []
        for d, it in sorted(w24h or mentions[-MAX_EVIDENCE_URLS:], key=lambda pair: pair[0], reverse=True):
            if it.get("url") and it["url"] not in evidence_urls:
                evidence_urls.append(it["url"])
            if len(evidence_urls) >= MAX_EVIDENCE_URLS:
                break

        rows.append({
            "key": key, "label": ent.get("label") or key, "type": ent.get("type"),
            "mentions_1h": len(w1h), "mentions_4h": len(w4h), "mentions_24h": len(w24h),
            "unique_events_4h": _unique_events(w4h), "unique_events_24h": _unique_events(w24h),
            "unique_sources_4h": _unique_sources(w4h), "unique_sources_24h": _unique_sources(w24h),
            "source_diversity_24h": _unique_sources(w24h),
            "acceleration": acceleration,
            "baseline_7d": baseline_7d,
            "baseline_daily_7d": baseline_daily_7d,
            "momentum": momentum,
            "baseline_30d": None,  # nessuna fonte ha 30gg pieni su tutte le entita' (C4/D0.2): non e' una misura
            "share_of_voice_24h": round(len(w24h) / total_24h, 3) if total_24h else None,
            "last_event_at": mentions[-1][0].isoformat().replace("+00:00", "Z") if mentions else None,
            "top_events": top_events,
            "evidence": evidence_urls,
        })
    return rows


def export_trending_json(rows):
    """MEDIA_PILOT_FINAL_HANDOFF.md §15: schema pubblico per la dashboard, un oggetto per entita'
    (non per articolo — vedi nota architetturale in cima al file per il perche' non e' lo
    schema-item di rassegna.json). Solo le entita' con attivita' reale nelle ultime 24h: le altre
    51 (su 55) restano nel file interno `trending_entities.jsonl` per audit, non qui — stessa
    logica di `export_rassegna()` che esporta solo gli item `is_relevant`, non tutto il corpus."""
    active = [r for r in rows if r["mentions_24h"] > 0 or r["mentions_4h"] > 0]
    active.sort(key=lambda r: (r["momentum"] if r["momentum"] is not None else -999, r["mentions_24h"]), reverse=True)
    entries = [{
        "entity_id": r["key"], "label": r["label"],
        "mentions_24h": r["mentions_24h"],
        "unique_events_24h": r["unique_events_24h"],
        "unique_sources_24h": r["unique_sources_24h"],
        "baseline_7d": r["baseline_daily_7d"],  # media giornaliera, vedi nota su compute_trending
        "momentum": r["momentum"],
        "last_event_at": r["last_event_at"],
        "top_events": r["top_events"],
        "evidence": r["evidence"],
    } for r in active]
    TRENDING_ASSET_JSON.parent.mkdir(parents=True, exist_ok=True)
    TRENDING_ASSET_JSON.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"{TRENDING_ASSET_JSON.relative_to(ROOT)} scritto: {len(entries)} entita' attive nelle ultime 24h")
    return entries


def run():
    items = load_scored_items()
    sources_by_id = load_sources_by_id()
    entities = load_entities_yaml()
    rows = compute_trending(items, sources_by_id, entities)
    TRENDING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(TRENDING_JSONL, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    active_24h = sum(1 for r in rows if r["mentions_24h"] > 0)
    with_baseline = sum(1 for r in rows if r["baseline_7d"] is not None)
    print(f"entita' nel registry: {len(rows)} | con mention nelle ultime 24h: {active_24h} | "
          f"con baseline_7d misurabile: {with_baseline}")
    top = sorted(rows, key=lambda r: (r["acceleration"] or 0, r["mentions_24h"]), reverse=True)[:20]
    print("\ntop 20 per acceleration (poi mentions_24h):")
    for r in top:
        print(f"  {r['key']:20s} accel={r['acceleration']}  mentions_24h={r['mentions_24h']}  "
              f"baseline_7d={r['baseline_7d']}  eventi_24h={r['unique_events_24h']}  fonti_24h={r['unique_sources_24h']}")
    return rows


if __name__ == "__main__":
    run()
