"""Rilancia SOLO le annotazioni B (deepseek) ancora fallite (_review=True) in
data/golden/annotations_b.jsonl. Resumable: salva su disco dopo OGNI item, non solo alla
fine — se il processo si interrompe (chiusura PC, Ctrl+C, crash), rilanciarlo semplicemente
di nuovo riprende dai soli item ancora falliti, senza ripetere quelli gia' riusciti.
"""
import json
import sys
from pathlib import Path

from pilot.golden.annotate import ANNOTATIONS_B, SAMPLE_JSONL, annotate_item


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def save_jsonl(path, records):
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(path)  # scrittura atomica: mai un file a meta'


def main():
    sample_by_id = {r["raw_id"]: r for r in load_jsonl(SAMPLE_JSONL)}
    b_records = load_jsonl(ANNOTATIONS_B)

    to_retry = [i for i, r in enumerate(b_records) if r.get("_review")]
    print(f"totale: {len(b_records)} | gia' riusciti: {len(b_records) - len(to_retry)} | da ritentare: {len(to_retry)}")

    done_this_run = 0
    for idx in to_retry:
        rec = b_records[idx]
        item = sample_by_id[rec["raw_id"]]
        try:
            result = annotate_item(item, "deepseek")
        except KeyboardInterrupt:
            print("\ninterrotto dall'utente, stato gia' salvato fino a questo punto.")
            sys.exit(1)
        b_records[idx] = {"raw_id": item["raw_id"], "title": item["title"], "url": item["url"], **result}
        save_jsonl(ANNOTATIONS_B, b_records)  # salvataggio immediato: resumable ad ogni riga
        done_this_run += 1
        print(f"[{done_this_run}/{len(to_retry)}] {item['raw_id'][:8]} review={result.get('_review')}")

    still_failed = sum(1 for r in b_records if r.get("_review"))
    print(f"\nfatti in questa run: {done_this_run} | ancora falliti dopo il retry: {still_failed}/{len(b_records)}")
    if still_failed:
        print("rilanciare lo stesso script per ritentare solo questi ultimi.")


if __name__ == "__main__":
    main()
