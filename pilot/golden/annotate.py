"""§2 — Doppia annotazione indipendente: due chiamate separate (Anthropic, DeepSeek), stesso
prompt, nessuna vede la risposta dell'altra. Se il parsing JSON fallisce: REVIEW, mai un
valore riparato a caso (vedi parse_json_or_review).
"""
import argparse
import json
import re
from pathlib import Path

from pilot.llm import llm

ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_JSONL = ROOT / "data" / "golden" / "sample.jsonl"
ANNOTATIONS_A = ROOT / "data" / "golden" / "annotations_a.jsonl"
ANNOTATIONS_B = ROOT / "data" / "golden" / "annotations_b.jsonl"

PROVIDERS = ("anthropic", "deepseek")


def parse_json_or_review(raw, required_keys):
    """Estrae e valida un oggetto JSON dalla risposta del modello. Qualunque fallimento
    (nessuna chiave API, risposta vuota, JSON non valido, chiave mancante) produce un record
    marcato _review=True con il motivo — mai un valore riparato a caso."""
    if raw is None:
        return {"_review": True, "_reason": "no_response"}
    m = re.search(r"\{.*\}", raw.strip(), re.S)
    if not m:
        return {"_review": True, "_reason": "no_json_found", "_raw": raw[:500]}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"_review": True, "_reason": "json_decode_error", "_raw": raw[:500]}
    for k in required_keys:
        if k not in obj:
            return {"_review": True, "_reason": f"missing_key_{k}", "_raw": raw[:500]}
    obj["_review"] = False
    return obj


def call_both_providers(fn):
    """Chiama fn('anthropic') poi fn('deepseek'), completamente indipendenti: fn deve
    ricostruire il prompt da zero ad ogni chiamata, nessuno stato condiviso fra le due."""
    return fn("anthropic"), fn("deepseek")


ANNOTATE_PROMPT = """Leggi questo articolo in serbo/bosniaco e rispondi SOLO con un oggetto JSON valido,
senza altro testo, in questo formato esatto:
{{"is_political": true|false, "entities": ["nome proprio 1", "nome proprio 2"], "gloss_it": "una riga in italiano", "confidence": 0.0-1.0}}

Regole:
- is_political = riguarda partiti, candidati, istituzioni, elezioni, campagna elettorale, relazioni
  fra soggetti politici. Cronaca nera, sport, salute, meteo, economia generica: false.
- entities = SOLO nomi propri effettivamente presenti nel testo (persone, partiti, istituzioni con
  nome proprio). Mai dedotti, mai impliciti. Una sigla generica senza riferimento istituzionale
  esplicito (es. "BiH" da sola) non e' un'entita'.
- gloss_it = una sola riga in italiano che riassume il fatto, per chi non legge il serbo.
- Se sei in dubbio, confidence bassa. Non indovinare.

Titolo: {title}
Testo: {text}
"""


def annotate_item(item, provider):
    prompt = ANNOTATE_PROMPT.format(title=item["title"], text=item["text"][:1500])
    raw = llm(prompt, max_tokens=300, provider=provider)
    return parse_json_or_review(raw, required_keys=("is_political", "entities", "gloss_it"))


def load_sample():
    items = []
    with open(SAMPLE_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def run_annotation(sample_items):
    a_records, b_records = [], []
    for idx, item in enumerate(sample_items):
        judged_a, judged_b = call_both_providers(lambda p: annotate_item(item, p))
        base = {"raw_id": item["raw_id"], "title": item["title"], "url": item["url"]}
        a_records.append({**base, **judged_a})
        b_records.append({**base, **judged_b})
        print(f"[{idx + 1}/{len(sample_items)}] {item['raw_id'][:8]} "
              f"A.is_political={judged_a.get('is_political')} B.is_political={judged_b.get('is_political')} "
              f"review_a={judged_a.get('_review')} review_b={judged_b.get('_review')}")
    return a_records, b_records


def main():
    sample_items = load_sample()
    a_records, b_records = run_annotation(sample_items)
    with open(ANNOTATIONS_A, "w", encoding="utf-8") as f:
        for r in a_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(ANNOTATIONS_B, "w", encoding="utf-8") as f:
        for r in b_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nscritte {len(a_records)} annotazioni in annotations_a.jsonl / annotations_b.jsonl")


if __name__ == "__main__":
    main()
