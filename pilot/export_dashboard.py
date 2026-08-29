"""Beta: collega l'output del pilot alla dashboard, scrivendo assets/data/rassegna.json nello
schema che data.js/radar.js si aspettano. NON tocca nessun file della dashboard (letti soltanto,
come dashboard-config.js altrove nel pilot).

Scope deliberatamente ridotto per una prima connessione: sostituisce SOLO rassegna.json (il
livello base che UI.buildCorpus() unisce a cases.json) con dati reali da data/scored_items.jsonl.
trending.json/signals.json/alerts.json/cases.json/tasks.json/archive.json/candidates.json restano
la demo esistente — sono viste derivate o dati a cura umana (VRH), non qualcosa che il pilot deve
generare in questo passo. Vedi report FIX_01 per il perche' dello scope ridotto.

Campi di giudizio (risk/opportunity/wedge/owner/deadline/suggested_responses/signal_to_vrh/
signal_to_media/user_info) restano ai valori di default "assente" — MAI inventati, stessa regola
di score.py._FORBIDDEN_LAYER3_FIELDS. radar.js e ui.js sono gia' difensivi su questi campi
(fallback a 0/[]/false/stringa vuota), verificato leggendo il codice prima di scrivere questo file.
"""
import json
from pathlib import Path

from pilot.entities import DASHBOARD_CONFIG, build_territory_cards, parse_c_calls, parse_ij_names

ROOT = Path(__file__).resolve().parent.parent
SCORED_ITEMS_JSONL = ROOT / "data" / "scored_items.jsonl"
SCORED_CLUSTERS_JSONL = ROOT / "data" / "scored_clusters.jsonl"
RASSEGNA_JSON = ROOT / "assets" / "data" / "rassegna.json"
# pagina di prova, output del pilot: NON e' una pagina della dashboard, sta in data/ apposta
PREVIEW_HTML = ROOT / "data" / "rassegna_preview.html"

_JUDGMENT_DEFAULTS = {
    "risk": 0, "opportunity": 0, "wedge": 0, "owner": None, "deadline": None,
    "signal_to_vrh": False, "signal_to_media": False, "suggested_responses": [],
    "user_info": None,
}

_PREVIEW_TEMPLATE = """<!doctype html>
<html lang="sr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rassegna — anteprima pilot</title>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#16181d;--mut:#6b7280;--line:#e5e7eb;--chip:#eef2ff;--acc:#1d4ed8}
@media(prefers-color-scheme:dark){:root{--bg:#111318;--fg:#e8eaed;--mut:#9aa1ac;--line:#2a2f38;--chip:#1e2534;--acc:#7ea2ff}}
*{box-sizing:border-box}
body{margin:0;padding:24px;background:var(--bg);color:var(--fg);
  font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
h1{font-size:19px;margin:0 0 4px}
.sub{color:var(--mut);font-size:13px;margin-bottom:16px}
.stats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.stat{border:1px solid var(--line);border-radius:8px;padding:8px 12px;min-width:96px}
.stat b{display:block;font-size:20px;font-variant-numeric:tabular-nums}
.stat span{color:var(--mut);font-size:12px}
input{width:100%;max-width:420px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;
  background:var(--bg);color:var(--fg);font:inherit;margin-bottom:14px}
.wrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:9px 12px;border-bottom:1px solid var(--line);vertical-align:top}
th{position:sticky;top:0;background:var(--bg);font-size:12px;color:var(--mut);
  text-transform:uppercase;letter-spacing:.04em}
tr:last-child td{border-bottom:0}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.mod{display:inline-block;background:var(--chip);border-radius:5px;padding:1px 6px;
  font-size:11px;margin:0 3px 3px 0}
.warn{border-left:3px solid var(--acc);background:var(--chip);padding:10px 14px;
  border-radius:0 8px 8px 0;font-size:13px;margin-bottom:18px}
.warn code{font-size:12px}
</style></head><body>
<h1>Rassegna — anteprima sui dati veri</h1>
<div class="sub">Output di <code>pilot.export_dashboard</code>. Non e' la dashboard: e' una pagina
di prova per guardare i dati ordinati per <code>signal_score</code>.</div>
<div class="stats" id="stats"></div>
<div class="warn"><b>Cosa NON c'e', di proposito:</b> i campi di giudizio
(<code>risk</code>, <code>opportunity</code>, <code>wedge</code>, <code>signal_to_vrh</code>) sono a
cura umana e restano ai default; <code>territory_ij</code> resta <code>null</code> perche' le IJ non
sono verificate. <code>signal_score</code> oggi ha pochi valori distinti: e' il problema aperto
di <code>TASK_BETA_02</code> C1.</div>
<input id="q" placeholder="filtra per titolo, fonte o card (es. SNSD, CIK, RTRS)" autofocus>
<div class="wrap"><table>
<thead><tr><th class="n">#</th><th class="n">score</th><th>data</th><th>titolo</th>
<th>fonte</th><th class="n">cluster</th><th>card</th></tr></thead>
<tbody id="rows"></tbody></table></div>
<script>
var DATA = __DATA__, STATS = __STATS__;
var LABEL = {item:"item", con_card:"con card", fonti:"fonti", giorni:"giorni",
             score_distinti:"score distinti", score_max:"score max"};
document.getElementById("stats").innerHTML = Object.keys(STATS).map(function(k){
  return '<div class="stat"><b>' + STATS[k] + '</b><span>' + (LABEL[k] || k) + '</span></div>';
}).join("");
function esc(s){ return String(s == null ? "" : s).replace(/[&<>"]/g, function(c){
  return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]; }); }
function render(q){
  q = (q || "").toLowerCase();
  var out = [], n = 0;
  for (var i = 0; i < DATA.length; i++){
    var e = DATA[i];
    var hay = (e.title + " " + (e.source_note || "") + " " + (e.modules || []).join(" ")).toLowerCase();
    if (q && hay.indexOf(q) < 0) continue;
    n++;
    if (n > 400) continue;  // la pagina resta leggera: si filtra, non si scorre all'infinito
    out.push('<tr><td class="n">' + n + '</td>'
      + '<td class="n">' + (e.signal_score == null ? "—" : e.signal_score.toFixed(1)) + '</td>'
      + '<td class="n">' + esc((e.date || "").slice(0, 10)) + '</td>'
      + '<td>' + (e.url ? '<a href="' + esc(e.url) + '" target="_blank" rel="noopener">'
                        + esc(e.title) + '</a>' : esc(e.title)) + '</td>'
      + '<td>' + esc(e.source_note) + '</td>'
      + '<td class="n">' + (e.cluster_size || 1) + (e.n_copies > 1 ? " ×" + e.n_copies : "") + '</td>'
      + '<td>' + (e.modules || []).map(function(m){ return '<span class="mod">' + esc(m) + '</span>'; }).join("")
      + '</td></tr>');
  }
  if (!out.length) out.push('<tr><td colspan="7">nessun item</td></tr>');
  else if (n > 400) out.push('<tr><td colspan="7">... e altri ' + (n - 400)
    + ' item: restringi il filtro</td></tr>');
  document.getElementById("rows").innerHTML = out.join("");
}
document.getElementById("q").addEventListener("input", function(e){ render(e.target.value); });
render("");
</script></body></html>
"""


def load_jsonl(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_key_to_dashboard_modules():
    """Chiave entita' (es. 'predsjednistvo') -> codici card.modules di dashboard-config.js
    (es. ['CIK','IZB']). entities.yaml non porta questa info (scartata da generate_entities),
    quindi si rilegge dashboard-config.js direttamente, come fa gia' entities.py."""
    js_text = DASHBOARD_CONFIG.read_text(encoding="utf-8")
    ij_names = parse_ij_names(js_text)
    cards = parse_c_calls(js_text) + build_territory_cards(ij_names)
    return {c["key"]: c["modules"] for c in cards}


def excerpt(text, max_len=280):
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def build_rassegna_entry(it, key_to_modules, cluster=None):
    dashboard_modules = sorted({code for key in it.get("modules", []) for code in key_to_modules.get(key, [])})
    entry = {
        "id": it["raw_id"],
        # C0: il punteggio si calcolava e non arrivava mai alla dashboard, che quindi non poteva
        # ordinare per rilevanza. E' l'unico campo MISURATO che si aggiunge qui: i campi di
        # giudizio restano ai default in _JUDGMENT_DEFAULTS.
        "signal_score": (cluster or {}).get("signal_score"),
        "cluster_size": len((cluster or {}).get("items") or []) or None,
        "menu": it.get("menu"),
        "date": it.get("published_at"),
        "title": it.get("title") or "",
        "modules": dashboard_modules,
        "territory": it.get("territory_raw"),
        "territory_ij": it.get("territory_ij"),
        "summary": excerpt(it.get("text")),
        "source_note": ", ".join(it.get("source_ids") or []),
        "verification": it.get("verification"),
        "provenance": it.get("provenance"),
        "origin_type": it.get("origin_type"),
        "n_copies": it.get("n_copies"),
        "cluster_id": it.get("cluster_id"),
        "url": it.get("url"),
    }
    entry.update(_JUDGMENT_DEFAULTS)
    return entry


def export_rassegna():
    items = load_jsonl(SCORED_ITEMS_JSONL)
    # C0: si esportano SOLO gli item rilevanti. Prima uscivano tutti, inclusi i 732 scartati dal
    # filtro di rilevanza: misurato, dei 459 item che mappano su una card della dashboard 459 su
    # 459 erano rilevanti, quindi gli altri diluivano la rassegna senza portare niente.
    items = [it for it in items if it.get("is_relevant")]
    cluster_by_id = {c["cluster_id"]: c for c in load_jsonl(SCORED_CLUSTERS_JSONL)}
    key_to_modules = build_key_to_dashboard_modules()
    entries = [build_rassegna_entry(it, key_to_modules, cluster_by_id.get(it.get("cluster_id"))) for it in items]
    entries.sort(key=lambda e: (-(e["signal_score"] or 0.0), e["date"] or ""))
    RASSEGNA_JSON.parent.mkdir(parents=True, exist_ok=True)
    RASSEGNA_JSON.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    with_modules = sum(1 for e in entries if e["modules"])
    with_score = sum(1 for e in entries if e["signal_score"] is not None)
    print(f"rassegna.json scritto: {len(entries)} item rilevanti | con modules dashboard: {with_modules} "
          f"({100 * with_modules // max(len(entries), 1)}%) | con signal_score: {with_score}")
    write_preview_html(entries)
    return entries


def write_preview_html(entries):
    """Pagina di prova autosufficiente sui dati veri: nessuna dipendenza, nessun file della
    dashboard toccato. Serve a guardare la rassegna ordinata per signal_score prima di collegarla
    davvero al frontend."""
    scores = [e["signal_score"] for e in entries if e["signal_score"] is not None]
    stats = {
        "item": len(entries),
        "con_card": sum(1 for e in entries if e["modules"]),
        "fonti": len({s for e in entries for s in (e["source_note"] or "").split(", ") if s}),
        "giorni": len({(e["date"] or "")[:10] for e in entries if e["date"]}),
        "score_distinti": len(set(scores)),
        "score_max": max(scores) if scores else 0,
    }
    html = _PREVIEW_TEMPLATE.replace("__STATS__", json.dumps(stats, ensure_ascii=False))
    html = html.replace("__DATA__", json.dumps(entries, ensure_ascii=False))
    PREVIEW_HTML.write_text(html, encoding="utf-8", newline="\n")
    print(f"anteprima scritta: {PREVIEW_HTML.relative_to(ROOT)}")


if __name__ == "__main__":
    export_rassegna()
