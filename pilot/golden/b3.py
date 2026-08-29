"""B3 §1 — Estensione del golden set con coppie dal corpus nuovo (post B1/B2), priorita' alle
coppie come richiesto da TASK_BETA_01.md B3.1.

Non tocca sample.py/pairs.py/review.py/build.py (regola FIX_00: "nessuno di questi file va
riscritto"). Riusa le loro funzioni pure e monkeypatcha i path a modulo di review.py/build.py
per farli scrivere in data/golden_b3/ invece che in data/golden/, cosi' il golden set originale
(100 item, 58 coppie, gia' consolidato) resta intatto.

Scope volutamente ridotto rispetto a sample.py: solo coppie (dup-like + campione event-like +
negativo), niente annotazione item-level is_political/entities — B3 la chiede solo per le coppie
("le soglie di dedup/clustering sono tarate su n=5 duplicati e n=3 stesso-evento").
"""
import argparse
import json
import random
from pathlib import Path

from pilot.golden.annotate import call_both_providers
from pilot.golden.pairs import generate_candidate_pairs, judge_pair, load_items

ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN_JSONL = ROOT / "data" / "clean.jsonl"
OLD_SAMPLE_JSONL = ROOT / "data" / "golden" / "sample.jsonl"

B3_DIR = ROOT / "data" / "golden_b3"
POOL_JSONL = B3_DIR / "pairs_pool.jsonl"
SAMPLE_JSONL = B3_DIR / "sample.jsonl"
PAIRS_A = B3_DIR / "pairs_a.jsonl"
PAIRS_B = B3_DIR / "pairs_b.jsonl"

SEED = 42
DUP_MAX = 42          # tutte le dup-like trovate (>=0.90) nel corpus attuale
EVENT_SAMPLE = 40     # campione da 1298 event-like (0.35-0.90)
NEGATIVE_SAMPLE = 30  # campione sotto soglia, come nella run originale


def _old_ids():
    if not OLD_SAMPLE_JSONL.exists():
        return set()
    return {json.loads(l)["raw_id"] for l in OLD_SAMPLE_JSONL.open(encoding="utf-8") if l.strip()}


def generate():
    """Genera pairs_pool.jsonl + sample.jsonl (solo item referenziati dalle coppie scelte)."""
    old_ids = _old_ids()
    items = load_items(CLEAN_JSONL)
    by_id = {it["raw_id"]: it for it in items}
    pairs, all_scored = generate_candidate_pairs(items)

    def is_new(a, b):
        return a not in old_ids or b not in old_ids

    dup = [p for p in pairs if p[2] >= 0.90 and is_new(p[0], p[1])]
    event = [p for p in pairs if 0.35 <= p[2] < 0.90 and is_new(p[0], p[1])]
    below = [p for p in all_scored if p[2] < 0.35 and is_new(p[0], p[1])]

    rng = random.Random(SEED)
    rng.shuffle(dup)
    rng.shuffle(event)
    rng.shuffle(below)

    dup_pick = dup[:DUP_MAX]
    event_pick = event[:EVENT_SAMPLE]
    neg_pick = below[:NEGATIVE_SAMPLE]
    pool = dup_pick + event_pick + neg_pick

    B3_DIR.mkdir(parents=True, exist_ok=True)
    with open(POOL_JSONL, "w", encoding="utf-8") as f:
        for a, b, s in pool:
            f.write(json.dumps({"raw_id_a": a, "raw_id_b": b, "blocking_score": round(s, 4)}, ensure_ascii=False) + "\n")

    ref_ids = {rid for a, b, _ in pool for rid in (a, b)}
    with open(SAMPLE_JSONL, "w", encoding="utf-8") as f:
        for rid in ref_ids:
            it = by_id[rid]
            f.write(json.dumps({
                "raw_id": rid, "title": it["title"], "text": it["text"], "url": it.get("url"),
                "source_id": it["source_id"], "published_at": it.get("published_at"),
            }, ensure_ascii=False) + "\n")

    print(f"candidate totali sopra soglia 0.35 (esclusi entrambi-vecchi): dup={len(dup)} event={len(event)}")
    print(f"pool scelto: dup={len(dup_pick)} event={len(event_pick)} negativo={len(neg_pick)} totale={len(pool)}")
    print(f"item referenziati: {len(ref_ids)} -> {SAMPLE_JSONL}")


def judge():
    if not POOL_JSONL.exists():
        raise SystemExit("lancia prima --generate")
    items_by_id = {it["raw_id"]: it for it in load_items(CLEAN_JSONL)}
    pool = [json.loads(l) for l in POOL_JSONL.open(encoding="utf-8") if l.strip()]
    a_records, b_records = [], []
    for idx, p in enumerate(pool):
        id_a, id_b, score = p["raw_id_a"], p["raw_id_b"], p["blocking_score"]
        item_a, item_b = items_by_id.get(id_a), items_by_id.get(id_b)
        if not item_a or not item_b:
            continue
        judged_a, judged_b = call_both_providers(lambda prov: judge_pair(item_a, item_b, prov))
        base = {"pair_id": f"{id_a}__{id_b}", "raw_id_a": id_a, "raw_id_b": id_b, "blocking_score": score}
        a_records.append({**base, **judged_a})
        b_records.append({**base, **judged_b})
        print(f"[{idx + 1}/{len(pool)}] {id_a[:8]}/{id_b[:8]} score={score:.2f} A={judged_a.get('label')} B={judged_b.get('label')}")
    with open(PAIRS_A, "w", encoding="utf-8") as f:
        for r in a_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(PAIRS_B, "w", encoding="utf-8") as f:
        for r in b_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"giudizi scritti: {len(a_records)} coppie in pairs_a.jsonl/pairs_b.jsonl")


def _patch_review_and_build_paths():
    """Ripunta i path a modulo di review.py/build.py a data/golden_b3/, senza toccare i file.
    review.py resta l'unica sorgente di verita' per la logica (agreement/spotcheck/decisioni);
    qui si sovrascrivono solo i Path globali prima di usarne le funzioni."""
    import pilot.golden.review as review_mod
    review_mod.GOLDEN_DIR = B3_DIR
    review_mod.SAMPLE_JSONL = SAMPLE_JSONL
    review_mod.ANNOTATIONS_A = B3_DIR / "annotations_a.jsonl"  # non usate in B3 (solo coppie), file assente = []
    review_mod.ANNOTATIONS_B = B3_DIR / "annotations_b.jsonl"
    review_mod.PAIRS_A = PAIRS_A
    review_mod.PAIRS_B = PAIRS_B
    review_mod.DECISIONS_JSONL = B3_DIR / "decisions.jsonl"
    review_mod.SPOTCHECK_IDS_JSON = B3_DIR / "spotcheck_ids.json"
    return review_mod


def serve_review(port=8766):
    review_mod = _patch_review_and_build_paths()
    from http.server import ThreadingHTTPServer
    server = ThreadingHTTPServer(("127.0.0.1", port), review_mod.Handler)
    print(f"B3 review UI su http://localhost:{port} (Ctrl+C per fermare) — coppie dal corpus nuovo, non l'estensione originale")
    state = review_mod.compute_state()
    print(f"Coda disaccordi: {len(state['queue1_disagreement'])} da decidere ({state['total_disagreements']} totali)")
    print(f"Coda controllo: {len(state['queue2_spotcheck'])} da decidere ({state['total_spotcheck']} totali)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def build():
    _patch_review_and_build_paths()
    import pilot.golden.build as build_mod
    out = build_mod.consolidate()  # scrive gia' da solo in build_mod.OUT_PATH (= B3_DIR/golden_dataset.json, patchato)
    print(f"scritto {build_mod.OUT_PATH}")
    print(json.dumps(out["metrics"], ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--build", action="store_true")
    args = ap.parse_args()
    if args.generate:
        generate()
    if args.judge:
        judge()
    if args.review:
        serve_review()
    if args.build:
        build()
    if not any((args.generate, args.judge, args.review, args.build)):
        ap.print_help()


if __name__ == "__main__":
    main()
