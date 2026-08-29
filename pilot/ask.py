"""§7 — python -m pilot.ask "domanda" --days 7

BM25 su chunks_fts, un cluster = una voce. Con chiave LLM: sintesi con [1][2] mappati agli
url in fondo. Senza chiave: passaggi trovati con url e data. Mai una risposta senza url.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pilot.llm import llm
from pilot.util import normalize_search

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "corpus.db"
TOP_K = 8


def _fts_query(query_norm):
    terms = [t for t in query_norm.split() if len(t) > 2]
    if not terms:
        return None
    return "(" + " OR ".join(f'"{t}"' for t in terms) + ")"


def retrieve(question, days=7, top_k=TOP_K):
    if not DB_PATH.exists():
        return []
    query_norm = normalize_search(question)
    match_expr = _fts_query(query_norm)
    if not match_expr:
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    rows = conn.execute(
        """
        SELECT chunks_fts.raw_id, chunks_fts.source_id, chunks_fts.published_at, chunks_fts.cluster_id,
               bm25(chunks_fts, 5.0, 1.0, 1.0, 0, 0, 0, 0, 0) AS rank,
               items.title, items.url, items.text
        FROM chunks_fts JOIN items ON items.raw_id = chunks_fts.raw_id
        WHERE chunks_fts MATCH ?
        ORDER BY rank LIMIT 100
        """,
        (f"{{title_norm text_norm}} : {match_expr}",),
    ).fetchall()
    conn.close()

    filtered = [r for r in rows if not r["published_at"] or r["published_at"] >= since]
    seen_clusters = set()
    results = []
    for r in filtered:
        cid = r["cluster_id"] or r["raw_id"]
        if cid in seen_clusters:
            continue
        seen_clusters.add(cid)
        results.append(dict(r))
        if len(results) >= top_k:
            break
    return results


def format_no_llm(question, hits):
    if not hits:
        return "nessun documento nel corpus"
    lines = [f'Passaggi trovati per: "{question}"\n']
    for i, h in enumerate(hits, 1):
        snippet = h["text"][:280].replace("\n", " ").strip()
        lines.append(f"[{i}] {h['title']}")
        lines.append(f"    {snippet}...")
        lines.append(f"    fonte: {h['source_id']} | {h.get('published_at') or 'data sconosciuta'} | {h['url']}")
        lines.append("")
    return "\n".join(lines)


def format_with_llm(question, hits):
    numbered_sources = "\n".join(
        f"[{i}] {h['title']} ({h['source_id']}, {h.get('published_at') or 'data sconosciuta'}): {h['text'][:1000]}"
        for i, h in enumerate(hits, 1)
    )
    prompt = (
        "Rispondi alla domanda usando SOLO le fonti numerate qui sotto. "
        "Ogni affermazione deve avere una citazione [n] che corrisponde alla fonte. "
        "Se le fonti non bastano per rispondere, dillo esplicitamente. Rispondi in serbo/bosniaco.\n\n"
        f"Domanda: {question}\n\nFonti:\n{numbered_sources}\n\nRisposta:"
    )
    answer = llm(prompt)
    if answer is None:
        return None
    footer = "\n\nFonti:\n" + "\n".join(
        f"[{i}] {h['url']} ({h.get('published_at') or 'data sconosciuta'})" for i, h in enumerate(hits, 1)
    )
    return answer + footer


def ask(question, days=7):
    hits = retrieve(question, days=days)
    if not hits:
        return "nessun documento nel corpus"
    with_llm = format_with_llm(question, hits)
    if with_llm is not None:
        return with_llm
    return format_no_llm(question, hits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    print(ask(args.question, days=args.days))


if __name__ == "__main__":
    main()
