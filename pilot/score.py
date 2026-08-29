"""§6 — Assegnazione valore: tre strati separati, mai mescolati nello stesso oggetto.

Strato 1 (misurato), Strato 2 (derivato per regole), Strato 3 (giudizio, assente per default).
Legge data/items.jsonl + data/clusters.jsonl, scrive data/scored_items.jsonl + data/scored_clusters.jsonl.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pilot import miniyaml
from pilot.entities import _exact_word_match, load_entities_yaml, load_weak_keywords, match_entities
from pilot.util import normalize_search

ROOT = Path(__file__).resolve().parent.parent
ITEMS_JSONL = ROOT / "data" / "items.jsonl"
CLUSTERS_JSONL = ROOT / "data" / "clusters.jsonl"
ENTITIES_YAML = ROOT / "config" / "entities.yaml"
SOURCES_YAML = ROOT / "config" / "sources.yaml"
SCORING_YAML = ROOT / "config" / "scoring.yaml"
SCORED_ITEMS_JSONL = ROOT / "data" / "scored_items.jsonl"
SCORED_CLUSTERS_JSONL = ROOT / "data" / "scored_clusters.jsonl"

_FORBIDDEN_LAYER3_FIELDS = {
    "risk", "opportunity", "wedge", "risk_score", "create_case", "human_review",
    "signal_to_vrh", "signal_to_media", "owner", "deadline", "suggested_responses", "user_info",
}

# menu del dashboard (5 categorie fisse: news/social/local/institutions/campaign, vedi radar.js
# RASSEGNA_MENUS). Match esatto per i source_type che non seguono un prefisso ("regional_portal",
# "local_tv_radio": locali ma senza prefisso "local_"; "election_monitoring"/"ngo_monitoring":
# organismi di vigilanza, non media — "institutions" e' la lettura piu' diretta del nome, non
# inventata). Il prefisso resta come fallback per source_type non ancora visti.
_MENU_EXACT = {
    "regional_portal": "local", "local_tv_radio": "local",
    "election_monitoring": "institutions", "ngo_monitoring": "institutions",
}
_MENU_PREFIX = [("media_", "news"), ("local_", "local"), ("official_", "institutions"), ("party_", "campaign")]

_PROVENANCE_BY_TYPE = {
    "official_local": "OFFICIAL", "party_official": "OFFICIAL", "election_monitoring": "OFFICIAL",
    "ngo_monitoring": "MANUAL",
}


def load_jsonl(path):
    out = []
    if not path.exists():
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def load_entities():
    return load_entities_yaml()


def load_sources_by_id():
    doc = miniyaml.load(SOURCES_YAML)
    return {s["source_id"]: s for s in doc.get("sources", [])}


def load_scoring():
    return miniyaml.load(SCORING_YAML) if SCORING_YAML.exists() else {}


def menu_for(tip_izvora):
    if tip_izvora in _MENU_EXACT:
        return _MENU_EXACT[tip_izvora]
    for prefix, menu in _MENU_PREFIX:
        if tip_izvora and tip_izvora.startswith(prefix):
            return menu
    return None  # nessuna regola per questo tip_izvora: mai inventato, vedi report


def provenance_for(tip_izvora):
    return _PROVENANCE_BY_TYPE.get(tip_izvora, "MEDIA")


def _dt(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def compute_layer2(items, entities, sources_by_id):
    weak_keywords_norm = load_weak_keywords()
    for it in items:
        src = sources_by_id.get(it["source_id"], {})
        tip = src.get("source_type")
        # il filtro di rilevanza (dedup.py, prima del clustering) ha gia' calcolato gli hit per
        # ogni item passato dalla pipeline reale: qui si ricalcola solo se mancano (es. nei test).
        if "_entity_hits" in it:
            hits = it["_entity_hits"]
        else:
            hits = match_entities(it.get("title", ""), it.get("text", ""), entities, weak_keywords_norm)
        it["modules"] = sorted({h["key"] for h in hits})
        it["_entity_hits"] = hits  # uso interno per entity_centrality, rimosso prima dell'output
        it["menu"] = menu_for(tip)
        it["provenance"] = provenance_for(tip)
        it["verification"] = (
            "OFFICIAL_CONFIRMED" if provenance_for(tip) == "OFFICIAL" and it["n_copies"] >= 1
            else "MULTI_SOURCE" if len(it["source_ids"]) > 1
            else "SINGLE_SOURCE"
        )
        it["territory_raw"] = None  # nessuna estrazione di territorio in questo pilot: zero invenzione
        it["territory_ij"] = None  # §D.3: le IJ non sono verificate, MAI dedotto
        # §3, punto 2: n_copies>1 (dedup ha trovato lo stesso testo su piu' fonti) e' il segnale
        # meccanico di rilancio d'agenzia disponibile in questo pilot — non identifica SRNA/FENA
        # specificamente (nessun feed agenzia tracciato), ma la firma operativa e' la stessa:
        # contenuto identico su piu' fonti non e' conferma editoriale indipendente.
        it["origin_type"] = "agency_repost" if it["n_copies"] > 1 else "original_reporting"
    return items


def _bucket_4h(d):
    b = d.replace(minute=0, second=0, microsecond=0)
    return b.replace(hour=(b.hour // 4) * 4)


def compute_layer1_and_signal(items, clusters, sources_by_id, weights, max_items_per_group=3):
    owner_by_source = {sid: (s.get("owner_group")) for sid, s in sources_by_id.items()}
    items_by_id = {it["raw_id"]: it for it in items}

    # baseline di velocity: mediana di item/4h su tutta la finestra raccolta (7d = 42 bucket da 4h).
    # B0: i bucket VUOTI vanno contati. Contando solo quelli con almeno un articolo la mediana misura
    # "quanto pubblicano quando pubblicano", non il ritmo medio, e sovrastima la baseline: sul corpus
    # del 2026-08-28 (28 bucket non vuoti su 48) dava 6 invece di 2.
    all_dts = sorted(d for d in (_dt(it.get("published_at")) for it in items) if d)
    bucket_counts = {}
    if all_dts:
        b, last = _bucket_4h(all_dts[0]), _bucket_4h(all_dts[-1])
        while b <= last:
            bucket_counts[b] = 0
            b += timedelta(hours=4)
        for d in all_dts:
            bucket_counts[_bucket_4h(d)] += 1
    counts_sorted = sorted(bucket_counts.values())
    baseline_4h = counts_sorted[len(counts_sorted) // 2] if counts_sorted else 1
    baseline_4h = max(baseline_4h, 1)

    now = max(all_dts) if all_dts else datetime.now(timezone.utc)

    # §4, punto 3: la baseline sopra e' calcolata sull'intero corpus in ingresso, quindi la sua
    # finestra reale e' quella del corpus stesso (giorni civili UTC distinti coperti), non quella
    # di una singola fonte. Sotto i 3 giorni la mediana/4h non e' statisticamente significativa.
    window_actual_days = len({d.date() for d in all_dts})
    baseline_incomplete = window_actual_days < 3

    for c in clusters:
        member_items = [items_by_id[i] for i in c["items"] if i in items_by_id]
        if not member_items:
            continue
        owner_groups = {owner_by_source.get(sid) or sid for sid in c["sources"]}
        source_diversity = len(owner_groups)

        is_local = lambda it: (sources_by_id.get(it["source_id"], {}).get("source_type") or "").startswith(("local", "regional"))
        has_local = any(is_local(it) for it in member_items)
        has_national_or_official = any(not is_local(it) for it in member_items)
        source_jump = bool(has_local and has_national_or_official)

        # §3, punto 4: tetto per fonte/gruppo su velocity, indipendente da owner_group (che resta
        # null, non accertabile). Conta i GRUPPI distinti con almeno un articolo recente, non gli
        # articoli: altrimenti due emittenti ad alto volume (RTRS+ATV, 68% del corpus) potrebbero
        # da sole far apparire "in tendenza" qualunque cosa ripubblichino piu' volte.
        # B0: numeratore e denominatore devono avere la STESSA unita'. baseline_4h conta ITEM per
        # bucket da 4h, quindi qui si contano ARTICOLI. FIX 3 aveva cambiato il numeratore in gruppi
        # di fonti (1-4) lasciando il denominatore in item (6): velocity assumeva 2 soli valori,
        # 0.0 e 0.167 (= 1/6), cioe' era un flag di recency a 4h, non una velocita'. Il tetto
        # anti-gonfiaggio di FIX 3 resta ma come CAP: una singola emittente che ripubblica venti
        # volte vale al massimo max_items_per_group articoli, quindi RTRS+ATV non possono da sole
        # far sembrare "in tendenza" qualunque cosa ripubblichino.
        recent = [it for it in member_items
                  if _dt(it.get("published_at")) and (now - _dt(it.get("published_at"))) <= timedelta(hours=4)]
        recent_groups = {owner_by_source.get(it["source_id"]) or it["source_id"] for it in recent}
        cluster_4h_count = min(len(recent), len(recent_groups) * max_items_per_group)
        velocity = None if baseline_incomplete else (round(cluster_4h_count / baseline_4h, 3) if baseline_4h else None)
        # C3, TASK_BETA_02, 2026-08-28: la versione pesata e continua di velocity resta in
        # `measured` per audit (dipende da una baseline a mediana debole, vedi B0), ma il segnale
        # che entra nel punteggio e' il flag booleano sotto: RFC_SECONDA_OPINIONE_02.md §5.3
        # misura un tetto strutturale, solo 8-21 cluster su ~500 hanno mai 2 articoli in 4h -
        # troppo pochi per una componente continua, sufficienti per un flag onesto "sta uscendo
        # adesso".
        trending_now = cluster_4h_count >= 2

        all_entities = {}
        for it in member_items:
            for h in it.get("_entity_hits", []):
                all_entities[h["key"]] = max(all_entities.get(h["key"], 0.0), h["centrality"])
        entity_centrality = round(max(all_entities.values()), 3) if all_entities else 0.0

        dup_total = sum(it["n_copies"] for it in member_items)
        organic_weight = round(len(member_items) / dup_total, 3) if dup_total else 1.0

        # C3: `novelty` resta `None` per costruzione (richiede una baseline storica a 30gg che
        # oggi ha una sola fonte su 17, vedi C4) - tolta dal punteggio invece di restare una
        # componente sempre nulla, che il task esclude esplicitamente come opzione. Il campo resta
        # in `measured` solo per dichiarare che non e' implementata, mai per essere sommata.
        novelty = None

        # C3: pesi su scale separate apposta, non tutte a 1.0 come prima - source_diversity e' un
        # conteggio vero (1-8 su questo corpus) e resta l'unita' principale del punteggio; le altre
        # tre sono booleane/categoriche (4 livelli al massimo, vedi RFC §7 domanda 3) e contano come
        # bonus DENTRO lo stesso gradino di source_diversity, mai a cavallo: 0.3+0.2+0.1 = 0.6 < 1.0,
        # quindi due cluster con diversity diversa non collidono mai piu' per via dei pesi (prima
        # tutti a peso 1.0 su scale 0-1, un cluster con diversity+1 e uno con centrality+1.0 davano
        # la stessa somma - era questo, non i segnali stessi, a schiacciare signal_score a 16-17
        # valori). Misurato sul corpus reale: 24 valori distinti su 332 cluster (§C3 risultati),
        # contro un tetto reale di 24-25 combinazioni possibili di questi 4 segnali - non 50: la
        # differenza e' dichiarata nel report, non nascosta con altri pesi.
        components = {
            "source_diversity": round(source_diversity * weights.get("source_diversity", 1.0), 3),
            "trending_now": round((1.0 if trending_now else 0.0) * weights.get("trending_now", 0.2), 3),
            "source_jump": round((1.0 if source_jump else 0.0) * weights.get("source_jump", 0.1), 3),
            "entity_centrality": round(entity_centrality * weights.get("entity_centrality", 0.3), 3),
        }
        signal_score = round(sum(v for v in components.values() if v is not None), 3)

        c["measured"] = {
            "n_copies": dup_total,
            "source_diversity": source_diversity,
            "velocity": velocity,
            "velocity_baseline_4h": baseline_4h,
            "trending_now": trending_now,
            "source_jump": source_jump,
            "novelty": novelty,
            "entity_centrality": entity_centrality,
            "time_to_second_source": _time_to_second_source(member_items),
            "organic_weight": organic_weight,
            "window_actual_days": window_actual_days,
        }
        c["baseline_incomplete"] = baseline_incomplete
        c["signal_score"] = signal_score
        c["components"] = components
        c["entities"] = sorted(all_entities.keys())
    return clusters


def _time_to_second_source(member_items):
    times = sorted(_dt(it.get("published_at")) for it in member_items if it.get("published_at"))
    times = [t for t in times if t]
    if len(times) < 2:
        return None
    return round((times[1] - times[0]).total_seconds() / 60.0, 1)  # minuti


def strip_internal_fields(items):
    for it in items:
        it.pop("_entity_hits", None)
        it["judgment"] = {
            "risk": None, "impact": None, "urgency": None, "note": None,
            "provenance": "MODEL", "confidence": 0.0, "model": "", "prompt_version": "",
        }
        for field in _FORBIDDEN_LAYER3_FIELDS:
            it.pop(field, None)
    return items


def run():
    items = load_jsonl(ITEMS_JSONL)
    clusters = load_jsonl(CLUSTERS_JSONL)
    entities = load_entities()
    sources_by_id = load_sources_by_id()
    scoring_cfg = load_scoring()
    weights = scoring_cfg.get("signal_weights", {})

    items = compute_layer2(items, entities, sources_by_id)
    clusters = compute_layer1_and_signal(
        items, clusters, sources_by_id, weights,
        max_items_per_group=(scoring_cfg.get("velocity") or {}).get("max_items_per_group", 3),
    )
    items = strip_internal_fields(items)

    with open(SCORED_ITEMS_JSONL, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with open(SCORED_CLUSTERS_JSONL, "w", encoding="utf-8") as f:
        for c in clusters:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    matched = sum(1 for it in items if it["modules"])
    zero = len(items) - matched
    from collections import Counter
    counter = Counter()
    for it in items:
        counter.update(it["modules"])
    print(f"item con almeno un protagonista: {matched} | zero: {zero}")
    print("top 10 protagonisti:", counter.most_common(10))
    top_clusters = sorted(clusters, key=lambda c: c.get("signal_score") or 0, reverse=True)[:5]
    for c in top_clusters:
        print(c["cluster_id"], c.get("signal_score"), c.get("components"))
    return items, clusters


if __name__ == "__main__":
    run()
