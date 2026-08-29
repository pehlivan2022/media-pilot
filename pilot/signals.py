"""§H, MEDIA_PILOT_FINAL_HANDOFF.md — Signal Engine: SignalCandidate deterministici e spiegabili,
PER ENTITA' (come il Trending Engine, §D1/E in TASK_BETA_03). Un Signal e' "un cambiamento
significativo", non "un articolo con score alto" (§16). Legge data/trending_entities.jsonl (gia'
scritto da trending.run() nella stessa esecuzione di run_all) e ricalcola data/entity_salience.jsonl
(chiama entity_salience.run(): dipendenza interna, non un nuovo stadio nella catena di run_all.py).

Output: MONITORING o REVIEW (§16 — P1/P2_CANDIDATE "solo dopo test sufficienti", non qui).
Nessun LLM, nessun testo generato: `why_now` e' un template su numeri reali (§16: "nessun testo AI
e' necessario per produrlo"). `confidence` e' un CONTEGGIO di segnali misurati su 5, non una
probabilita' stimata — dichiarato come tale, per non dare falsa precisione a un numero regola-per-
regola.

Zero invenzione: nessun Alert/Case/P1 creato qui (§18: "il sistema propone, l'analista decide").
Un'entita' senza mention nelle ultime 24h non produce un Signal — il silenzio non e' un segnale."""
import json
from collections import defaultdict
from pathlib import Path

from pilot import entity_salience

ROOT = Path(__file__).resolve().parent.parent
TRENDING_JSONL = ROOT / "data" / "trending_entities.jsonl"
TRENDING_ASSET_JSON = ROOT / "assets" / "data" / "trending.json"
SIGNAL_CANDIDATES_JSONL = ROOT / "data" / "signal_candidates.jsonl"
SIGNALS_ASSET_JSON = ROOT / "assets" / "data" / "signals.json"
PREVIEW_HTML = ROOT / "data" / "trending_signals_preview.html"

# soglie dichiarate, non calibrate su un golden set (non esiste ancora un golden set di Signal
# umanamente confermati/respinti — la calibrazione e' un lavoro futuro, non "# da calibrare"
# nascosto: qui e' un punto di partenza esplicito, coerente con lo spirito del progetto di non
# fingere una misura che non c'e').
REVIEW_CONFIDENCE_MIN = 0.6
REVIEW_MENTIONS_MIN = 3
MOMENTUM_SIGNAL_MIN = 0.5
SOURCES_SIGNAL_MIN = 3
EVENTS_SIGNAL_MIN = 2
SALIENCE_SIGNAL_MIN = 1.0
CO_ENTITY_SIGNAL_MIN = 2


def load_trending_rows():
    rows = []
    with open(TRENDING_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _salience_summary_by_key(salience_rows):
    by_key = defaultdict(lambda: {"max_salience": 0.0, "any_primary": False, "max_co_entities": 0})
    for r in salience_rows:
        agg = by_key[r["key"]]
        agg["max_salience"] = max(agg["max_salience"], r["entity_salience"])
        agg["any_primary"] = agg["any_primary"] or r["is_primary_in_event"]
        agg["max_co_entities"] = max(agg["max_co_entities"], r["co_entities_in_event"])
    return by_key


def _why_now(components_fired, trend):
    parts = []
    if components_fired["momentum"]:
        parts.append(f"momentum {trend['momentum']:+.0%} vs normale" if trend["momentum"] is not None else "momentum in crescita")
    if components_fired["sources"]:
        parts.append(f"{trend['unique_sources_24h']} fonti indipendenti nelle ultime 24h")
    if components_fired["events"]:
        parts.append(f"{trend['unique_events_24h']} eventi distinti")
    if components_fired["salience"]:
        parts.append("entita' primaria/in titolo in almeno un articolo")
    if components_fired["cross_entity"]:
        parts.append("co-occorre con altre entita' tracciate nello stesso articolo")
    if not parts:
        parts.append(f"{trend['mentions_24h']} menzioni nelle ultime 24h, nessun'altra soglia superata")
    return "; ".join(parts)


def build_signal_candidates(trending_rows, salience_by_key):
    candidates = []
    for trend in trending_rows:
        if trend["mentions_24h"] <= 0:
            continue  # il silenzio non e' un segnale
        sal = salience_by_key.get(trend["key"], {"max_salience": 0.0, "any_primary": False, "max_co_entities": 0})

        components_fired = {
            "momentum": trend["momentum"] is not None and trend["momentum"] >= MOMENTUM_SIGNAL_MIN,
            "sources": trend["unique_sources_24h"] >= SOURCES_SIGNAL_MIN,
            "events": trend["unique_events_24h"] >= EVENTS_SIGNAL_MIN,
            "salience": sal["max_salience"] >= SALIENCE_SIGNAL_MIN or sal["any_primary"],
            "cross_entity": sal["max_co_entities"] >= CO_ENTITY_SIGNAL_MIN,
        }
        confidence = round(sum(components_fired.values()) / len(components_fired), 3)
        classification = (
            "REVIEW" if confidence >= REVIEW_CONFIDENCE_MIN and trend["mentions_24h"] >= REVIEW_MENTIONS_MIN
            else "MONITORING"
        )

        top_events = trend.get("top_events") or []
        first_seen = min((e["published_at"] for e in top_events if e.get("published_at")), default=None)

        candidates.append({
            "entity_id": trend["key"], "label": trend["label"], "classification": classification,
            "why_now": _why_now(components_fired, trend),
            "entities": [trend["key"]],
            "events": [e["cluster_id"] for e in top_events],
            "metrics": {
                "mentions_24h": trend["mentions_24h"], "unique_events_24h": trend["unique_events_24h"],
                "unique_sources_24h": trend["unique_sources_24h"], "momentum": trend["momentum"],
                "acceleration": trend["acceleration"], "max_entity_salience": round(sal["max_salience"], 3),
                "max_co_entities_in_event": sal["max_co_entities"],
            },
            "sources": sorted({e["source_id"] for e in top_events if e.get("source_id")}),
            "evidence": trend.get("evidence") or [],
            "first_seen": first_seen,
            "last_seen": trend["last_event_at"],
            "confidence": confidence,
            "confidence_components": components_fired,
            "provenance": "PILOT_RULES",  # meccanico, nessun LLM (§16/§17)
        })
    return candidates


def run():
    entity_salience.run()  # dipendenza interna: produce data/entity_salience.jsonl fresco
    with open(entity_salience.SALIENCE_JSONL, encoding="utf-8") as f:
        salience_rows = [json.loads(l) for l in f if l.strip()]
    salience_by_key = _salience_summary_by_key(salience_rows)

    trending_rows = load_trending_rows()
    candidates = build_signal_candidates(trending_rows, salience_by_key)

    SIGNAL_CANDIDATES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(SIGNAL_CANDIDATES_JSONL, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    n_review = sum(1 for c in candidates if c["classification"] == "REVIEW")
    print(f"signal candidates: {len(candidates)} ({n_review} REVIEW, {len(candidates) - n_review} MONITORING)")
    for c in sorted(candidates, key=lambda c: -c["confidence"])[:10]:
        print(f"  {c['entity_id']:20s} {c['classification']:11s} confidence={c['confidence']}  {c['why_now']}")
    return candidates


def export_signals_json(candidates):
    """Solo i REVIEW vanno in assets/data/signals.json (§11: 'Signal da guardare, solo quelli
    realmente rilevanti' — non tutti i MONITORING, che restano nel file interno per audit)."""
    review = [c for c in candidates if c["classification"] == "REVIEW"]
    SIGNALS_ASSET_JSON.parent.mkdir(parents=True, exist_ok=True)
    SIGNALS_ASSET_JSON.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"{SIGNALS_ASSET_JSON.relative_to(ROOT)} scritto: {len(review)} signal REVIEW")
    write_preview_html(review)
    return review


def _esc(s):
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def write_preview_html(review_signals):
    """Pagina di prova autosufficiente su Trending+Signal reali (stesso spirito di
    export_dashboard.write_preview_html per rassegna.json): NON e' una pagina della dashboard,
    nessuna dipendenza, nessun file frontend toccato. Serve a guardare i dati prima di deciderne
    il collegamento vero (§J, fuori scope qui: "no frontend rewrite")."""
    trending = json.loads(TRENDING_ASSET_JSON.read_text(encoding="utf-8")) if TRENDING_ASSET_JSON.exists() else []
    rows_trend = "".join(
        f"<tr><td>{_esc(e['entity_id'])}</td><td>{_esc(e['label'])}</td>"
        f"<td class='n'>{e['mentions_24h']}</td><td class='n'>{e['unique_events_24h']}</td>"
        f"<td class='n'>{e['unique_sources_24h']}</td>"
        f"<td class='n'>{'' if e['momentum'] is None else format(e['momentum'], '+.0%')}</td>"
        f"<td>{' · '.join('<a href=' + chr(34) + _esc(u) + chr(34) + ' target=_blank>fonte</a>' for u in e['evidence'][:3])}</td></tr>"
        for e in trending
    )
    rows_signal = "".join(
        f"<tr><td>{_esc(c['entity_id'])}</td><td>{_esc(c['why_now'])}</td>"
        f"<td class='n'>{c['confidence']}</td><td>{' · '.join(_esc(s) for s in c['sources'])}</td>"
        f"<td>{' · '.join('<a href=' + chr(34) + _esc(u) + chr(34) + ' target=_blank>fonte</a>' for u in c['evidence'][:3])}</td></tr>"
        for c in review_signals
    )
    html = f"""<!doctype html>
<html lang="sr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trending + Signal — anteprima pilot</title>
<style>
:root{{color-scheme:light dark;--bg:#fff;--fg:#16181d;--mut:#6b7280;--line:#e5e7eb;--acc:#1d4ed8}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111318;--fg:#e8eaed;--mut:#9aa1ac;--line:#2a2f38;--acc:#7ea2ff}}}}
*{{box-sizing:border-box}}
body{{margin:0;padding:24px;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}}
h1{{font-size:19px;margin:24px 0 4px}}h1:first-of-type{{margin-top:0}}
.sub{{color:var(--mut);font-size:13px;margin-bottom:12px}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin-bottom:24px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}}
th{{font-size:12px;color:var(--mut);text-transform:uppercase}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
a{{color:var(--acc)}}
</style></head><body>
<h1>Trending per entita' ({len(trending)} attive nelle ultime 24h)</h1>
<div class="sub">Output di <code>pilot.trending</code>. Non e' la dashboard.</div>
<div class="wrap"><table><thead><tr><th>entita'</th><th>label</th><th class="n">menzioni 24h</th>
<th class="n">eventi</th><th class="n">fonti</th><th class="n">momentum</th><th>evidence</th></tr></thead>
<tbody>{rows_trend}</tbody></table></div>
<h1>Signal REVIEW ({len(review_signals)})</h1>
<div class="sub">Output di <code>pilot.signals</code>. MONITORING+REVIEW completi in
data/signal_candidates.jsonl. Nessun Alert/Case creato: proposta, non decisione.</div>
<div class="wrap"><table><thead><tr><th>entita'</th><th>perche' adesso</th>
<th class="n">confidence</th><th>fonti</th><th>evidence</th></tr></thead>
<tbody>{rows_signal}</tbody></table></div>
</body></html>
"""
    PREVIEW_HTML.write_text(html, encoding="utf-8", newline="\n")
    print(f"anteprima scritta: {PREVIEW_HTML.relative_to(ROOT)}")


if __name__ == "__main__":
    export_signals_json(run())
