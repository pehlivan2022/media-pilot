"""§7 — Indice RAG: SQLite FTS5 su title_norm/text_norm. Ricostruisce data/corpus.db da zero.

Un articolo = un chunk. Si spezza solo sopra ~1500 caratteri, a paragrafo, overlap di una frase.
"""
import json
import re
import sqlite3
from pathlib import Path

from pilot.util import normalize_search

ROOT = Path(__file__).resolve().parent.parent
SCORED_ITEMS_JSONL = ROOT / "data" / "scored_items.jsonl"
DB_PATH = ROOT / "data" / "corpus.db"

CHUNK_MAX_CHARS = 1500


def load_items():
    items = []
    with open(SCORED_ITEMS_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def split_into_chunks(text):
    """Un item = un chunk, salvo testo > ~1500 char: allora spezza a paragrafo con overlap
    di una frase. Articoli corti non si spezzano (si perderebbe contesto)."""
    if len(text) <= CHUNK_MAX_CHARS:
        return [text]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    prev_sentence = ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para).strip() if current else para
        if len(candidate) > CHUNK_MAX_CHARS and current:
            chunks.append(current)
            sentences = re.split(r"(?<=[.!?])\s+", current)
            prev_sentence = sentences[-1] if sentences else ""
            current = (prev_sentence + " " + para).strip()
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def build_index():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE items (
            raw_id TEXT PRIMARY KEY, source_id TEXT, url TEXT, title TEXT, text TEXT,
            published_at TEXT, cluster_id TEXT, entities TEXT, modules TEXT,
            evidence TEXT, n_copies INTEGER
        )
    """)
    conn.execute("""
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            title_norm, text_norm, entities,
            raw_id UNINDEXED, source_id UNINDEXED, published_at UNINDEXED,
            cluster_id UNINDEXED, chunk_index UNINDEXED
        )
    """)

    items = load_items()
    n_chunks = 0
    for it in items:
        conn.execute(
            "INSERT OR REPLACE INTO items VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (it["raw_id"], it["source_id"], it["url"], it["title"], it["text"],
             it.get("published_at"), it.get("cluster_id"), json.dumps(it.get("modules") or []),
             json.dumps(it.get("modules") or []), json.dumps(it.get("evidence") or []), it.get("n_copies", 1)),
        )
        chunks = split_into_chunks(it["text"])
        entities_str = " ".join(it.get("modules") or [])
        for idx, chunk_text in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks_fts (title_norm, text_norm, entities, raw_id, source_id, published_at, cluster_id, chunk_index) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (it["title_norm"] if idx == 0 else "", normalize_search(chunk_text), entities_str,
                 it["raw_id"], it["source_id"], it.get("published_at"), it.get("cluster_id"), idx),
            )
            n_chunks += 1
    conn.commit()
    conn.close()
    print(f"data/corpus.db costruito: {len(items)} item -> {n_chunks} chunk")
    return len(items), n_chunks


if __name__ == "__main__":
    build_index()
