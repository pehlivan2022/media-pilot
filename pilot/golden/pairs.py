"""§3 — Coppie candidate (blocking a soglia larga) + campione negativo + giudizio a due modelli.

generate_candidate_pairs() e' l'UNICO punto in cui la pipeline tocca il golden set (ammesso dal
task solo per restringere il campo, non per etichettare: la soglia 0.35 e' deliberatamente piu'
bassa di quelle reali in config/scoring.yaml).
"""
import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from pilot.golden.annotate import call_both_providers, parse_json_or_review
from pilot.llm import llm

ROOT = Path(__file__).resolve().parent.parent.parent
CLEAN_JSONL = ROOT / "data" / "clean.jsonl"
SAMPLE_JSONL = ROOT / "data" / "golden" / "sample.jsonl"
PAIRS_A = ROOT / "data" / "golden" / "pairs_a.jsonl"
PAIRS_B = ROOT / "data" / "golden" / "pairs_b.jsonl"

NGRAM_N = 5
BLOCKING_THRESHOLD = 0.35
WINDOW_HOURS = 72
NEGATIVE_SAMPLE_SIZE = 50
SEED = 42


def char_ngrams(text, n=NGRAM_N):
    text = (text or "").lower()
    if len(text) < n:
        return {text} if text else set()
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _dt(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def load_items(path=CLEAN_JSONL):
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def generate_candidate_pairs(items, threshold=BLOCKING_THRESHOLD, window_hours=WINDOW_HOURS):
    """Sliding window per tempo (sort by published_at) + n-gram Jaccard sul corpo.
    O(n * finestra), non O(n^2): la finestra temporale scarta la maggior parte delle coppie
    prima ancora di calcolare la similarita'."""
    dated = [(it, _dt(it.get("published_at"))) for it in items]
    dated = [(it, dt) for it, dt in dated if dt is not None]
    dated.sort(key=lambda x: x[1])
    ngrams_cache = {}

    def ngrams_of(it):
        if it["raw_id"] not in ngrams_cache:
            ngrams_cache[it["raw_id"]] = char_ngrams(it.get("text", ""))
        return ngrams_cache[it["raw_id"]]

    pairs = []
    all_pairs_scored = []  # tutte le coppie nella finestra temporale, anche sotto soglia (per il negativo)
    window = timedelta(hours=window_hours)
    for i, (it_i, dt_i) in enumerate(dated):
        for j in range(i + 1, len(dated)):
            it_j, dt_j = dated[j]
            if dt_j - dt_i > window:
                break
            score = jaccard(ngrams_of(it_i), ngrams_of(it_j))
            all_pairs_scored.append((it_i["raw_id"], it_j["raw_id"], score))
            if score >= threshold:
                pairs.append((it_i["raw_id"], it_j["raw_id"], score))
    return pairs, all_pairs_scored


def sample_negative_pairs(all_pairs_scored, threshold=BLOCKING_THRESHOLD, n=NEGATIVE_SAMPLE_SIZE, seed=SEED):
    below = [p for p in all_pairs_scored if p[2] < threshold]
    rng = random.Random(seed)
    rng.shuffle(below)
    return below[:n]


PAIR_PROMPT = """Confronta questi due articoli in serbo/bosniaco e classifica la relazione.
Rispondi SOLO con un oggetto JSON valido, senza altro testo:
{{"label": "DUPLICATO" | "STESSO_EVENTO" | "DIVERSI", "confidence": 0.0-1.0}}

DUPLICATO = stesso articolo, ripubblicato o riscritto (stesso fatto specifico, stessa fonte primaria).
STESSO_EVENTO = articoli diversi ma sullo stesso fatto/evento concreto.
DIVERSI = fatti diversi, anche se argomenti simili.

Articolo A:
Titolo: {title_a}
Testo: {text_a}

Articolo B:
Titolo: {title_b}
Testo: {text_b}
"""


def judge_pair(item_a, item_b, provider):
    prompt = PAIR_PROMPT.format(
        title_a=item_a["title"], text_a=item_a["text"][:1200],
        title_b=item_b["title"], text_b=item_b["text"][:1200],
    )
    raw = llm(prompt, max_tokens=100, provider=provider)
    parsed = parse_json_or_review(raw, required_keys=("label",))
    return parsed


def run_judgment(pool):
    items_by_id = {it["raw_id"]: it for it in load_items()}
    a_records, b_records = [], []
    for idx, (id_a, id_b, score) in enumerate(pool):
        item_a, item_b = items_by_id.get(id_a), items_by_id.get(id_b)
        if not item_a or not item_b:
            continue
        judged_a, judged_b = call_both_providers(lambda p: judge_pair(item_a, item_b, p))
        base = {"pair_id": f"{id_a}__{id_b}", "raw_id_a": id_a, "raw_id_b": id_b, "blocking_score": round(score, 4)}
        a_records.append({**base, **judged_a})
        b_records.append({**base, **judged_b})
        print(f"[{idx + 1}/{len(pool)}] {id_a[:8]}/{id_b[:8]} score={score:.2f} A={judged_a.get('label')} B={judged_b.get('label')}")
    return a_records, b_records


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="esegue anche il giudizio LLM sulle coppie (chiama le API)")
    args = ap.parse_args()

    items = load_items()
    pairs, all_scored = generate_candidate_pairs(items)
    negatives = sample_negative_pairs(all_scored)
    pool = pairs + negatives
    print(f"item nella finestra 72h con coppie valutate: {len(all_scored)} coppie totali")
    print(f"coppie sopra soglia {BLOCKING_THRESHOLD}: {len(pairs)} | campione negativo sotto soglia: {len(negatives)}")

    pool_path = ROOT / "data" / "golden" / "pairs_pool.jsonl"
    with open(pool_path, "w", encoding="utf-8") as f:
        for id_a, id_b, score in pool:
            f.write(json.dumps({"raw_id_a": id_a, "raw_id_b": id_b, "blocking_score": round(score, 4)}, ensure_ascii=False) + "\n")
    print(f"pool scritto in {pool_path.name}: {len(pool)} coppie")

    if args.judge:
        a_records, b_records = run_judgment(pool)
        with open(PAIRS_A, "w", encoding="utf-8") as f:
            for r in a_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(PAIRS_B, "w", encoding="utf-8") as f:
            for r in b_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"giudizi scritti: {len(a_records)} in pairs_a.jsonl / pairs_b.jsonl")


if __name__ == "__main__":
    main()
