"""§1 — Campione stratificato per il golden set. Seed fisso, riproducibile.

Il criterio di stratificazione (nome proprio nel titolo, coppie dal blocking, script, sigle
ambigue) serve SOLO a scegliere quali item mostrare ai modelli: non e' l'etichetta finale
(che arriva da annotate.py/pairs.py). Riusa config/entities.yaml solo per campionare, mai per
etichettare (guardrail del task).
"""
import argparse
import json
import random
import re
from pathlib import Path

from pilot import miniyaml
from pilot.golden.pairs import generate_candidate_pairs, load_items
from pilot.util import has_cyrillic, normalize_search

ROOT = Path(__file__).resolve().parent.parent.parent
ENTITIES_YAML = ROOT / "config" / "entities.yaml"
SAMPLE_JSONL = ROOT / "data" / "golden" / "sample.jsonl"
SAMPLING_REPORT = ROOT / "data" / "golden" / "sampling_report.json"

SEED = 42
QUOTAS = {
    "political": 20, "duplicate": 20, "event": 20,
    "non_political": 20, "cyr_latn": 10, "ambiguous": 10,
}
AMBIGUOUS_TERMS = ["us", "bih", "rs", "sp", "mandat", "finansiranje"]

# I quattro casi noti dalla prima run (§1, "Includere d'ufficio"). Il quarto (mandat non
# politico) non esiste come tale nel corpus reale di 245 item: il caso piu' vicino trovato
# e' un mandato diplomatico (Murphy/BiH), politico ma nel senso ambiguo/borderline richiesto
# dalla categoria "sigle ambigue" — sostituzione dichiarata, non inventata.
FORCED_CASES = {
    "3e1865bf471970ceae2982e4": "non_political",  # Tragedija u BiH: Pcela usmrtila muskarca
    "183c81ce68a509adeee6c789": "non_political",  # Sramotan prizor u BiH: Rijekom tece krv?
    "844f00e228e0dacbd83f4558": "ambiguous",       # Djokovic stigao u Njujork (US Open)
    "71e8837723f7cce48436b257": "ambiguous",       # "Mandat u BiH istekao" (Murphy) - sostituto dichiarato
}


def match_entity_keys(title, text, entities):
    tnorm, xnorm = normalize_search(title), normalize_search(text[:300])
    for e in entities:
        for al in e["aliases"]:
            if al["exact_word_uppercase"]:
                rx = re.compile(r"(?<!\w)" + re.escape(al["text"]) + r"(?!\w)")
                if rx.search(title) or rx.search(text[:300]):
                    return True
            elif al["norm"] and (al["norm"] in tnorm or al["norm"] in xnorm):
                return True
    return False


def build_buckets(items, entities):
    by_id = {it["raw_id"]: it for it in items}
    pairs, all_scored = generate_candidate_pairs(items)
    dup_ids = {rid for a, b, s in pairs if s >= 0.90 for rid in (a, b)}
    event_ids = {rid for a, b, s in pairs if 0.35 <= s < 0.90 for rid in (a, b)} - dup_ids

    political, non_political = [], []
    for it in items:
        if it["raw_id"] in dup_ids or it["raw_id"] in event_ids:
            continue
        if match_entity_keys(it["title"], it["text"], entities):
            political.append(it["raw_id"])
        else:
            non_political.append(it["raw_id"])

    ambiguous = []
    for it in items:
        if it["raw_id"] in dup_ids or it["raw_id"] in event_ids:
            continue
        tnorm = normalize_search(it["title"])
        if any(re.search(r"(?<!\w)" + t + r"(?!\w)", tnorm) for t in AMBIGUOUS_TERMS):
            ambiguous.append(it["raw_id"])

    by_entity_script = {}
    for it in items:
        script = "cyrl" if has_cyrillic(it["title"]) else "latn"
        for e in entities:
            if match_entity_keys_single(it, e):
                by_entity_script.setdefault(e["key"], {"cyrl": [], "latn": []})[script].append(it["raw_id"])
    cyr_latn = []
    for key, scripts in by_entity_script.items():
        if scripts["cyrl"] and scripts["latn"]:
            cyr_latn.append((scripts["cyrl"][0], scripts["latn"][0]))

    return {
        "political": political, "non_political": non_political,
        "duplicate": list(dup_ids), "event": list(event_ids),
        "cyr_latn_pairs": cyr_latn, "ambiguous": ambiguous,
    }, by_id


def match_entity_keys_single(item, entity):
    tnorm, xnorm = normalize_search(item["title"]), normalize_search(item["text"][:300])
    for al in entity["aliases"]:
        if al["exact_word_uppercase"]:
            rx = re.compile(r"(?<!\w)" + re.escape(al["text"]) + r"(?!\w)")
            if rx.search(item["title"]) or rx.search(item["text"][:300]):
                return True
        elif al["norm"] and (al["norm"] in tnorm or al["norm"] in xnorm):
            return True
    return False


def sample(n=100, seed=SEED):
    items = load_items()
    entities = miniyaml.load(ENTITIES_YAML)["entities"]
    buckets, by_id = build_buckets(items, entities)
    rng = random.Random(seed)

    chosen = {}  # raw_id -> categoria
    report = {"planned_quotas": dict(QUOTAS), "actual_available": {}, "shortfall_redistributed": {}}

    def take(pool, k, category):
        rng.shuffle(pool)
        picked = pool[:k]
        for rid in picked:
            if rid not in chosen:
                chosen[rid] = category
        return picked

    dup_pool = list(buckets["duplicate"])
    event_pool = list(buckets["event"])
    cyr_latn_pairs = list(buckets["cyr_latn_pairs"])
    rng.shuffle(cyr_latn_pairs)
    ambiguous_pool = list(buckets["ambiguous"])
    political_pool = list(buckets["political"])
    non_political_pool = list(buckets["non_political"])

    take(dup_pool, QUOTAS["duplicate"], "duplicate")
    take(event_pool, QUOTAS["event"], "event")
    take(ambiguous_pool, QUOTAS["ambiguous"], "ambiguous")

    needed_pairs = QUOTAS["cyr_latn"] // 2
    for cyr_id, latn_id in cyr_latn_pairs[:needed_pairs]:
        chosen.setdefault(cyr_id, "cyr_latn")
        chosen.setdefault(latn_id, "cyr_latn")

    report["actual_available"] = {
        "duplicate": len(dup_pool), "event": len(event_pool),
        "cyr_latn_pairs_available": len(cyr_latn_pairs), "ambiguous": len(ambiguous_pool),
    }

    shortfall = 0
    for cat in ("duplicate", "event"):
        got = sum(1 for v in chosen.values() if v == cat)
        shortfall += max(0, QUOTAS[cat] - got)
    got_cyr_latn = sum(1 for v in chosen.values() if v == "cyr_latn")
    shortfall += max(0, QUOTAS["cyr_latn"] - got_cyr_latn)

    extra_political = shortfall // 2
    extra_non_political = shortfall - extra_political
    report["shortfall_redistributed"] = {
        "total_shortfall": shortfall, "extra_political": extra_political, "extra_non_political": extra_non_political,
    }

    take(political_pool, QUOTAS["political"] + extra_political, "political")
    take(non_political_pool, QUOTAS["non_political"] + extra_non_political, "non_political")

    for rid, cat in FORCED_CASES.items():
        if rid in by_id:
            chosen[rid] = chosen.get(rid, cat) if rid in chosen else cat
            chosen[rid] = cat  # forza sempre la presenza, sovrascrive la categoria di campionamento

    ids = list(chosen.keys())
    if len(ids) > n:
        rng.shuffle(ids)
        # tiene per certo i forced cases, poi riempie fino a n
        forced = [i for i in ids if i in FORCED_CASES]
        rest = [i for i in ids if i not in FORCED_CASES]
        ids = forced + rest[: n - len(forced)]
    elif len(ids) < n:
        remaining = [it["raw_id"] for it in items if it["raw_id"] not in chosen]
        rng.shuffle(remaining)
        for rid in remaining:
            if len(ids) >= n:
                break
            chosen[rid] = "filler_political_or_non_political"
            ids.append(rid)

    report["final_count"] = len(ids)
    report["category_counts"] = {}
    for rid in ids:
        cat = chosen[rid]
        report["category_counts"][cat] = report["category_counts"].get(cat, 0) + 1

    SAMPLE_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(SAMPLE_JSONL, "w", encoding="utf-8") as f:
        for rid in ids:
            it = by_id[rid]
            f.write(json.dumps({
                "raw_id": rid, "title": it["title"], "text": it["text"], "url": it["url"],
                "source_id": it["source_id"], "published_at": it.get("published_at"),
                "sampling_category": chosen[rid], "forced_case": rid in FORCED_CASES,
            }, ensure_ascii=False) + "\n")
    SAMPLING_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")

    print(f"campione scritto: {len(ids)} item in {SAMPLE_JSONL.name}")
    print("distribuzione:", report["category_counts"])
    print("shortfall (dichiarato, non riempito a occhio):", report["shortfall_redistributed"])
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    args = ap.parse_args()
    sample(n=args.n)


if __name__ == "__main__":
    main()
