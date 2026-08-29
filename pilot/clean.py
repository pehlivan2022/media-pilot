"""§4 — Pulizia e normalizzazione: legge data/raw/*.jsonl, scrive data/clean.jsonl.

Il testo originale non si tocca mai. title_norm/text_norm servono solo a cercare.
"""
import glob
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pilot.util import canonicalize_url, normalize_compare, sha256_hex

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
CLEAN_JSONL = ROOT / "data" / "clean.jsonl"
ERRORS_JSONL = ROOT / "data" / "errors.jsonl"

MIN_TEXT_LEN = 200

# La finestra di raccolta e' BACKFILL_DAYS_DEFAULT = 30 giorni (collect.py). Le pagine NON-articolo
# prese via sitemap (form WordPress, agenda eventi, archivi istituzionali, recensioni auto) portano
# il `lastmod` della pagina come published_at: misurati 26 item con date dal 1996 al luglio 2026.
# Non sono notizie, e sporcano window_actual_days (56 invece di 31) e i valori per fonte scritti in
# config/sources.yaml. Si scartano qui: e' pulizia del dato, non una misura.
# Item SENZA data si tengono: dato mancante != dato sbagliato (regola "zero invenzione").
# +/- 1 giorno di tolleranza su fusi e arrotondamenti dei feed.
STALE_DAYS = 30
_WINDOW_TOLERANCE = timedelta(days=1)

BOILERPLATE_PATTERNS = [
    r"^\s*Podijeli\s*[:.]?\s*$", r"^\s*Pro[cč]itajte (jo[sš]|vi[sš]e)\b.*$",
    r"^\s*Komentar[i]?\s*\(\d+\)\s*$", r"^\s*(Facebook|Twitter|Viber|WhatsApp)\s*$",
    r"^\s*Ovaj sajt koristi kolačiće.*$", r"^\s*Cookie.*polic.*$",
    r"^\s*Copyright\s*©?.*$", r"^\s*Sva prava zadr[zž]ana.*$",
    r"^\s*Izvor\s*:\s*\S+\s*$",
]
_BOILERPLATE_RE = [re.compile(p, re.I) for p in BOILERPLATE_PATTERNS]

# D0.1, TASK_BETA_03, 2026-08-28: BL_IJ3_006 (Banjaluka24) porta nel testo estratto il widget
# "articoli correlati" del template del sito — trafilatura non lo isola dal corpo. Misurato: 100/140
# raw item di questa fonte (71,4%, stesso numero gia' noto da B3.2/C1) contaminati, sempre
# nell'ultimo 15-22% del testo, sempre con la stessa firma strutturale: una riga "-" seguita da una
# riga indentata a tab "CategoriaNdana ago" / "CategoriaNsati ago" (es. "Politika2 dana ago...",
# "Hronika1 dan ago..."). Fix mirato a questa fonte, non all'estrazione globale (§D0.1: "non
# cambiare l'estrazione di tutte le fonti se non necessario") — taglia il testo alla prima
# occorrenza, verificato che nessuno dei 100 item scende sotto MIN_TEXT_LEN dopo il taglio.
_BL_IJ3_006_WIDGET_RE = re.compile(
    r"\n-\s*\n\s*[A-ZŠĐČĆŽ][a-zA-ZšđčćžŠĐČĆŽ]*\d+\s*(?:dan|dana|sat|sati)\s*ago"
)


def strip_source_specific(source_id, text):
    if source_id == "BL_IJ3_006" and text:
        m = _BL_IJ3_006_WIDGET_RE.search(text)
        if m:
            return text[: m.start()].rstrip()
    return text


def strip_boilerplate(text):
    if not text:
        return text
    lines = text.split("\n")
    kept = [ln for ln in lines if not any(rx.match(ln) for rx in _BOILERPLATE_RE)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(kept)).strip()


def log_error(kind, source_id, url, message):
    ERRORS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    rec = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": kind, "source_id": source_id, "url": url, "message": str(message)[:500], "retry_count": 0,
    }
    with open(ERRORS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_raw_items():
    items = []
    for path in sorted(glob.glob(str(RAW_DIR / "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
    return items


def _parse_dt(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def out_of_window(published_at, scraped_at):
    """True se published_at cade fuori dalla finestra di raccolta (vedi STALE_DAYS)."""
    p = _parse_dt(published_at)
    if p is None:
        return False
    ref = _parse_dt(scraped_at) or datetime.now(timezone.utc)
    age = ref - p
    return age > timedelta(days=STALE_DAYS) + _WINDOW_TOLERANCE or age < -_WINDOW_TOLERANCE


def clean_item(raw):
    published_at = raw.get("published_at")  # gia' normalizzato a UTC ISO da collect.py; mai dedotto qui
    # prima del controllo sul testo, cosi' il conteggio dei due scarti non si sovrappone
    if out_of_window(published_at, raw.get("scraped_at")):
        log_error("OUT_OF_WINDOW", raw["source_id"], raw.get("url", ""), f"published_at={published_at}")
        return None
    text = strip_source_specific(raw["source_id"], raw.get("text") or "")
    text = strip_boilerplate(text)
    if len(text) < MIN_TEXT_LEN:
        log_error("EMPTY_CONTENT", raw["source_id"], raw.get("url", ""), f"text_len={len(text)} < {MIN_TEXT_LEN}")
        return None
    canonical = canonicalize_url(raw.get("final_url") or raw.get("url"))
    item = {
        "raw_id": raw["raw_id"], "source_id": raw["source_id"],
        "url": raw.get("url"), "final_url": canonical,
        "title": raw.get("title") or "", "author": raw.get("author"),
        "text": text, "language": raw.get("language"), "script": raw.get("script"),
        "published_at": published_at, "occurred_at": None,  # mai dedotto (§4)
        "scraped_at": raw.get("scraped_at"),
        "content_hash": sha256_hex(text),
        "title_norm": normalize_compare(raw.get("title") or ""),
        "text_norm": normalize_compare(text),
    }
    return item


def clean(write=True):
    raw_items = load_raw_items()
    cleaned = []
    empty_count = 0
    stale_count = 0
    for raw in raw_items:
        if out_of_window(raw.get("published_at"), raw.get("scraped_at")):
            stale_count += 1
        item = clean_item(raw)
        if item is None:
            empty_count += 1
            continue
        cleaned.append(item)
    empty_count -= stale_count
    if write:
        CLEAN_JSONL.parent.mkdir(parents=True, exist_ok=True)
        with open(CLEAN_JSONL, "w", encoding="utf-8") as f:
            for item in cleaned:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"raw: {len(raw_items)} | puliti: {len(cleaned)} | EMPTY_CONTENT: {empty_count} | OUT_OF_WINDOW: {stale_count}")
    return cleaned


if __name__ == "__main__":
    clean()
