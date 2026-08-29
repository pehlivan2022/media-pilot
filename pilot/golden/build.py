"""§5 — Consolidamento: unisce annotazioni + coppie + decisioni umane in golden_dataset.json,
con label_source su ogni etichetta e il blocco di metriche di agreement richiesto dal report.
"""
import json
from pathlib import Path

from pilot.golden.pairs import BLOCKING_THRESHOLD
from pilot.golden.review import (
    DECISIONS_JSONL, GOLDEN_DIR, PAIRS_A, PAIRS_B, SAMPLE_JSONL,
    _load_jsonl, build_annotation_records, build_pair_records, get_or_create_spotcheck_ids,
)

OUT_PATH = GOLDEN_DIR / "golden_dataset.json"
POOL_JSONL = GOLDEN_DIR / "pairs_pool.jsonl"


def try_parse_other(text):
    text = (text or "").strip()
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return None


def consolidate():
    ann_agree, ann_disagree = build_annotation_records()
    pair_agree, pair_disagree = build_pair_records()
    all_agree = ann_agree + pair_agree
    spotcheck_ids = set(get_or_create_spotcheck_ids(all_agree))

    decisions = _load_jsonl(DECISIONS_JSONL)
    dec_by_key = {}
    for d in decisions:
        dec_by_key.setdefault((d["queue"], d["item_id"]), []).append(d)
    for key in dec_by_key:
        dec_by_key[key].sort(key=lambda d: d["timestamp"])  # ultima decisione vince se rifatta

    def latest_decision(queue, item_id):
        recs = dec_by_key.get((queue, item_id))
        return recs[-1] if recs else None

    final_items, final_pairs = [], []
    other_cases = []
    errors_found_in_spotcheck = 0
    spotcheck_decided = 0
    disagreements_resolved = 0

    counters = {"spotcheck_decided": 0, "errors_found": 0, "disagreements_resolved": 0}

    def resolve(rec, is_agree):
        item_id = rec["item_id"]
        if is_agree:
            if item_id in spotcheck_ids:
                dec = latest_decision("spotcheck", item_id)
                if dec is None:
                    return {**rec, "label_source": "AGREED", "models_agreed": True, "reviewed_by_human": False, "_pending": True}
                counters["spotcheck_decided"] += 1
                if dec["decision"] == "CONFIRMED":
                    return {**rec, "label_source": "AGREED_SPOT_CHECKED", "models_agreed": True, "reviewed_by_human": True}
                else:
                    counters["errors_found"] += 1
                    other_cases.append({"kind": rec["kind"], "item_id": item_id, "queue": "spotcheck",
                                         "decision": dec["decision"], "other_value": dec.get("other_value")})
                    return {**rec, "label_source": "HUMAN", "models_agreed": True, "reviewed_by_human": True,
                            "human_override": dec["decision"], "human_other_value": dec.get("other_value")}
            return {**rec, "label_source": "AGREED", "models_agreed": True, "reviewed_by_human": False}
        else:
            dec = latest_decision("disagreement", item_id)
            if dec is None:
                return {**rec, "label_source": "PENDING_REVIEW", "models_agreed": False, "reviewed_by_human": False, "_pending": True}
            counters["disagreements_resolved"] += 1
            chosen = dec["decision"]
            if chosen == "OTHER":
                other_cases.append({"kind": rec["kind"], "item_id": item_id, "queue": "disagreement",
                                     "decision": "OTHER", "other_value": dec.get("other_value")})
            return {**rec, "label_source": "HUMAN", "models_agreed": False, "reviewed_by_human": True,
                    "human_decision": chosen, "human_other_value": dec.get("other_value") if chosen == "OTHER" else None}

    for rec in ann_agree:
        final_items.append(resolve(rec, True))
    for rec in ann_disagree:
        final_items.append(resolve(rec, False))
    for rec in pair_agree:
        final_pairs.append(resolve(rec, True))
    for rec in pair_disagree:
        final_pairs.append(resolve(rec, False))

    # metriche di agreement (solo su annotazioni/coppie parse correttamente, mai su _review)
    valid_ann = [r for r in ann_agree + ann_disagree if not r["a"]["review"] and not r["b"]["review"]]
    political_matches = sum(1 for r in valid_ann if r["a"]["is_political"] == r["b"]["is_political"])
    agreement_is_political = political_matches / len(valid_ann) if valid_ann else None

    def jaccard(a, b):
        sa, sb = set(x.lower() for x in (a or [])), set(x.lower() for x in (b or []))
        if not sa and not sb:
            return 1.0
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    entity_jaccards = [jaccard(r["a"]["entities"], r["b"]["entities"]) for r in valid_ann]
    agreement_entities = sum(entity_jaccards) / len(entity_jaccards) if entity_jaccards else None

    valid_pairs = [r for r in pair_agree + pair_disagree if not r["a"]["review"] and not r["b"]["review"]]
    pair_matches = sum(1 for r in valid_pairs if r["a"]["label"] == r["b"]["label"])
    agreement_pairs = pair_matches / len(valid_pairs) if valid_pairs else None

    # coppie sotto soglia risultate positive (recall perso dal blocking)
    pool = _load_jsonl(POOL_JSONL)
    below_threshold_ids = {f"{p['raw_id_a']}__{p['raw_id_b']}" for p in pool if p["blocking_score"] < BLOCKING_THRESHOLD}
    positive_below = []
    for r in final_pairs:
        if r["item_id"] in below_threshold_ids:
            final_label = r.get("human_decision") or r.get("human_override") or r["a"]["label"]
            if final_label in ("DUPLICATO", "STESSO_EVENTO"):
                positive_below.append(r["item_id"])

    metrics = {
        "agreement_is_political_pct": round(agreement_is_political * 100, 1) if agreement_is_political is not None else None,
        "agreement_entities_jaccard_mean": round(agreement_entities, 3) if agreement_entities is not None else None,
        "agreement_pairs_pct": round(agreement_pairs * 100, 1) if agreement_pairs is not None else None,
        "disaccordi_risolti": counters["disagreements_resolved"],
        "disaccordi_totali": len(ann_disagree) + len(pair_disagree),
        "accordi_controllati": counters["spotcheck_decided"],
        "accordi_totali": len(all_agree),
        "accordi_controllati_pct": round(100 * counters["spotcheck_decided"] / len(all_agree), 1) if all_agree else None,
        "errori_trovati_nel_controllo": counters["errors_found"],
        "coppie_sotto_soglia_risultate_positive": len(positive_below),
        "coppie_sotto_soglia_totali_nel_pool": len(below_threshold_ids),
        "casi_altro_umano": other_cases,
    }

    pending = [r for r in final_items + final_pairs if r.get("_pending")]

    out = {"items": final_items, "pairs": final_pairs, "metrics": metrics, "pending_review_count": len(pending)}
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    return out


def main():
    out = consolidate()
    m = out["metrics"]
    print(f"golden_dataset.json scritto: {len(out['items'])} item, {len(out['pairs'])} coppie")
    print(f"pending (disaccordi/controlli non ancora decisi): {out['pending_review_count']}")
    print(json.dumps(m, ensure_ascii=False, indent=2))
    if m["agreement_is_political_pct"] is not None and m["agreement_is_political_pct"] < 80:
        print("\nATTENZIONE: agreement is_political sotto 80% — la definizione di 'politico' e' ambigua, non i modelli.")
    if m["accordi_controllati"] and m["errori_trovati_nel_controllo"] / m["accordi_controllati"] > 0.10:
        print("ATTENZIONE: oltre il 10% degli accordi controllati era sbagliato — il criterio dell'accordo non tiene, alzare il controllo al 50%.")


if __name__ == "__main__":
    main()
