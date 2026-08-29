"""§D2.2 TASK_BETA_03 — entity_salience: misura, non sostituisce `entity_centrality`.

`entity_centrality` (score.py) e' gia', di fatto, "trovato in titolo/lead/corpo" (match_entities
in entities.py assegna esattamente {"title":1.0,"lead":0.6,"body":0.3}) - 4 livelli inclusa
l'assenza. Il task chiede di misurare se aggiungere segnali osservabili (numero occorrenze, quante
altre entita' protagoniste nello stesso evento, se e' l'entita' primaria del cluster) dia piu'
granularita' in modo auditabile.

Legge data/items.jsonl (post-dedup, ha _entity_hits/cluster_id sugli item rilevanti — NON
scored_items.jsonl, che li ha gia' rimossi/aggregati), scrive data/entity_salience.jsonl: una riga
per (item, entita' citata). Non tocca score.py/scoring.yaml: e' una misura per decidere, non
un'integrazione automatica (il task lo vieta esplicitamente in questa fase)."""
import json
import re
from collections import defaultdict
from pathlib import Path

from pilot.entities import load_entities_yaml
from pilot.util import normalize_search

ROOT = Path(__file__).resolve().parent.parent
ITEMS_JSONL = ROOT / "data" / "items.jsonl"
SALIENCE_JSONL = ROOT / "data" / "entity_salience.jsonl"

_LOC_SCORE = {"title": 1.0, "lead": 0.6, "body": 0.3}
_CENTRALITY_TO_LOC = {v: k for k, v in _LOC_SCORE.items()}


def load_items():
    items = []
    with open(ITEMS_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def _occurrence_count(text_norm, aliases):
    """Conteggio approssimato per sottostringa sulle forme normalizzate degli alias: qui serve
    "quante volte se ne parla", non un match di rilevanza (quello lo fa gia' match_entities con
    i confini di parola) - un doppio conteggio occasionale su alias sovrapposti non cambia l'ordine
    di grandezza che interessa (0 vs 1 vs molte)."""
    seen_norms = set()
    total = 0
    for alias in aliases:
        norm = alias.get("norm")
        if not norm or norm in seen_norms:
            continue
        seen_norms.add(norm)
        total += text_norm.count(norm)
    return total


def compute_salience(items, entities):
    aliases_by_key = {e["key"]: e["aliases"] for e in entities}
    relevant = [it for it in items if it.get("is_relevant") and it.get("cluster_id")]

    # entita' per cluster (per co_entities_in_event / is_primary_in_event): un solo giro su tutti
    # gli item rilevanti, non uno per entita' - O(n), non O(n*entita').
    cluster_hits = defaultdict(list)  # cluster_id -> [(item, hit), ...]
    for it in relevant:
        for h in it.get("_entity_hits") or []:
            cluster_hits[it["cluster_id"]].append((it, h))

    rows = []
    for it in relevant:
        text_norm = normalize_search(it.get("text") or "")
        cluster_id = it["cluster_id"]
        cluster_entities = {h["key"] for _, h in cluster_hits[cluster_id]}
        max_centrality_in_cluster = max((h["centrality"] for _, h in cluster_hits[cluster_id]), default=0.0)
        for h in it.get("_entity_hits") or []:
            key = h["key"]
            loc = _CENTRALITY_TO_LOC.get(h["centrality"], "body")
            occ = _occurrence_count(text_norm, aliases_by_key.get(key, []))
            is_primary = h["centrality"] >= max_centrality_in_cluster
            salience = round(
                h["centrality"]  # posizione: titolo/lead/corpo, gia' 0.3-1.0
                + 0.1 * min(max(occ - 1, 0), 5)  # ripetizione: rendimenti decrescenti, tetto a 0.5
                + (0.15 if is_primary else 0.0)  # e' l'entita' che regge l'evento, non una citata di sfuggita
                , 3)
            rows.append({
                "raw_id": it["raw_id"], "cluster_id": cluster_id, "key": key,
                "found_in": loc, "occurrence_count": occ,
                "co_entities_in_event": len(cluster_entities) - 1,
                "is_primary_in_event": is_primary,
                "entity_salience": salience,
            })
    return rows


def run():
    items = load_items()
    entities = load_entities_yaml()
    rows = compute_salience(items, entities)
    with open(SALIENCE_JSONL, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    distinct_salience = len({r["entity_salience"] for r in rows})
    distinct_centrality_equiv = len({_LOC_SCORE[r["found_in"]] for r in rows})
    print(f"righe (item, entita' citata): {len(rows)}")
    print(f"valori distinti di entity_salience: {distinct_salience} "
          f"(vs {distinct_centrality_equiv} di solo found_in/entity_centrality)")

    # per-cluster: il MASSIMO di entity_salience sui membri, stesso ruolo che entity_centrality
    # gioca oggi in score.py - e' la statistica che conta per capire se sposterebbe signal_score.
    max_by_cluster = defaultdict(float)
    for r in rows:
        max_by_cluster[r["cluster_id"]] = max(max_by_cluster[r["cluster_id"]], r["entity_salience"])
    print(f"cluster con almeno un'entita': {len(max_by_cluster)} | "
          f"valori distinti di MAX(entity_salience) per cluster: {len(set(max_by_cluster.values()))}")
    return rows


if __name__ == "__main__":
    run()
