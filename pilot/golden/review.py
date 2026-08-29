"""§4 — UI di revisione: http.server stdlib + una pagina HTML. Nessuna dipendenza, nessun build.

Mostra solo cio' che richiede una decisione umana:
  CODA 1 - disaccordi fra i due modelli (annotazioni + coppie)
  CODA 2 - controllo a campione sul 20% degli accordi
Ogni decisione va subito su data/golden/decisions.jsonl: chiudere il browser non perde nulla.
"""
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_DIR = ROOT / "data" / "golden"
SAMPLE_JSONL = GOLDEN_DIR / "sample.jsonl"
ANNOTATIONS_A = GOLDEN_DIR / "annotations_a.jsonl"
ANNOTATIONS_B = GOLDEN_DIR / "annotations_b.jsonl"
PAIRS_A = GOLDEN_DIR / "pairs_a.jsonl"
PAIRS_B = GOLDEN_DIR / "pairs_b.jsonl"
DECISIONS_JSONL = GOLDEN_DIR / "decisions.jsonl"
SPOTCHECK_IDS_JSON = GOLDEN_DIR / "spotcheck_ids.json"
REVIEW_HTML = Path(__file__).resolve().parent / "review.html"

SPOTCHECK_FRACTION = 0.50
SPOTCHECK_SEED = 42


def _load_jsonl(path):
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out


def _entities_jaccard(a, b):
    sa, sb = set(x.lower() for x in (a or [])), set(x.lower() for x in (b or []))
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def load_decisions():
    return _load_jsonl(DECISIONS_JSONL)


def append_decision(record):
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    with open(DECISIONS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_annotation_records():
    sample_by_id = {s["raw_id"]: s for s in _load_jsonl(SAMPLE_JSONL)}
    a_by_id = {r["raw_id"]: r for r in _load_jsonl(ANNOTATIONS_A)}
    b_by_id = {r["raw_id"]: r for r in _load_jsonl(ANNOTATIONS_B)}
    agree, disagree = [], []
    for rid, s in sample_by_id.items():
        a, b = a_by_id.get(rid), b_by_id.get(rid)
        if a is None or b is None:
            continue
        rec = {
            "kind": "annotation", "item_id": rid, "title": s["title"], "text": s["text"][:600],
            "url": s["url"], "sampling_category": s.get("sampling_category"),
            "a": {"is_political": a.get("is_political"), "entities": a.get("entities"),
                  "gloss_it": a.get("gloss_it"), "confidence": a.get("confidence"), "review": a.get("_review")},
            "b": {"is_political": b.get("is_political"), "entities": b.get("entities"),
                  "gloss_it": b.get("gloss_it"), "confidence": b.get("confidence"), "review": b.get("_review")},
        }
        is_review = a.get("_review") or b.get("_review")
        same_political = a.get("is_political") == b.get("is_political")
        same_entities = _entities_jaccard(a.get("entities"), b.get("entities")) >= 0.5
        if is_review or not same_political or not same_entities:
            disagree.append(rec)
        else:
            agree.append(rec)
    return agree, disagree


def build_pair_records():
    a_by_id = {r["pair_id"]: r for r in _load_jsonl(PAIRS_A)}
    b_by_id = {r["pair_id"]: r for r in _load_jsonl(PAIRS_B)}
    sample_by_id = {s["raw_id"]: s for s in _load_jsonl(SAMPLE_JSONL)}
    clean_by_id = {}
    if not sample_by_id:
        clean_by_id = {}
    agree, disagree = [], []
    for pid, a in a_by_id.items():
        b = b_by_id.get(pid)
        if b is None:
            continue
        item_a = sample_by_id.get(a["raw_id_a"], {})
        item_b = sample_by_id.get(a["raw_id_b"], {})
        rec = {
            "kind": "pair", "item_id": pid, "blocking_score": a.get("blocking_score"),
            "title_a": item_a.get("title", a["raw_id_a"]), "text_a": item_a.get("text", "")[:400],
            "url_a": item_a.get("url", ""),
            "title_b": item_b.get("title", a["raw_id_b"]), "text_b": item_b.get("text", "")[:400],
            "url_b": item_b.get("url", ""),
            "a": {"label": a.get("label"), "confidence": a.get("confidence"), "review": a.get("_review")},
            "b": {"label": b.get("label"), "confidence": b.get("confidence"), "review": b.get("_review")},
        }
        is_review = a.get("_review") or b.get("_review")
        if is_review or a.get("label") != b.get("label"):
            disagree.append(rec)
        else:
            agree.append(rec)
    return agree, disagree


def get_or_create_spotcheck_ids(agreement_records):
    all_ids = sorted(r["item_id"] for r in agreement_records)
    if SPOTCHECK_IDS_JSON.exists():
        saved = json.loads(SPOTCHECK_IDS_JSON.read_text(encoding="utf-8"))
        saved_ids = set(saved.get("ids", []))
        # mantiene stabile la selezione salvata, ignora id non piu' presenti
        return [i for i in all_ids if i in saved_ids]
    rng = random.Random(SPOTCHECK_SEED)
    shuffled = list(all_ids)
    rng.shuffle(shuffled)
    k = max(1, round(len(all_ids) * SPOTCHECK_FRACTION)) if all_ids else 0
    chosen = shuffled[:k]
    SPOTCHECK_IDS_JSON.write_text(json.dumps({"ids": chosen, "fraction": SPOTCHECK_FRACTION}, ensure_ascii=False), encoding="utf-8")
    return chosen


def compute_state():
    ann_agree, ann_disagree = build_annotation_records()
    pair_agree, pair_disagree = build_pair_records()
    all_agree = ann_agree + pair_agree
    spotcheck_ids = set(get_or_create_spotcheck_ids(all_agree))
    spotcheck_records = [r for r in all_agree if r["item_id"] in spotcheck_ids]

    decided = load_decisions()
    decided_keys = {(d["queue"], d["item_id"]) for d in decided}

    disagreements = ann_disagree + pair_disagree
    queue1 = [r for r in disagreements if ("disagreement", r["item_id"]) not in decided_keys]
    queue2 = [r for r in spotcheck_records if ("spotcheck", r["item_id"]) not in decided_keys]

    return {
        "queue1_disagreement": queue1,
        "queue2_spotcheck": queue2,
        "total_disagreements": len(disagreements),
        "total_spotcheck": len(spotcheck_records),
        "decided_disagreements": sum(1 for d in decided if d["queue"] == "disagreement"),
        "decided_spotcheck": sum(1 for d in decided if d["queue"] == "spotcheck"),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # niente log su stderr per ogni richiesta statica

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            html = REVIEW_HTML.read_text(encoding="utf-8")
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/state":
            self._send_json(compute_state())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/decide":
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            required = {"queue", "item_id", "decision"}
            if not required.issubset(payload):
                self._send_json({"error": "campi mancanti"}, status=400)
                return
            from datetime import datetime, timezone
            payload["timestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            append_decision(payload)
            self._send_json({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Review UI su http://localhost:{port} (Ctrl+C per fermare)")
    state = compute_state()
    print(f"Coda disaccordi: {len(state['queue1_disagreement'])} da decidere ({state['total_disagreements']} totali)")
    print(f"Coda controllo: {len(state['queue2_spotcheck'])} da decidere ({state['total_spotcheck']} totali)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
