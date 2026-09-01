"""§3 — Raccolta reale dalle fonti config/sources.yaml, finestra now-7d UTC.

Append-only su data/raw/YYYY-MM-DD.jsonl. Una fonte rotta non blocca le altre.
Errori sempre espliciti in data/errors.jsonl, mai silenziosi.
"""
import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import feedparser
import trafilatura

from pilot import miniyaml
from pilot.util import FetchError, canonicalize_url, fetch, has_cyrillic, parse_date_to_utc, sha256_hex

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
MAX_LEAF_SITEMAPS = 6
MAX_BACKFILL_URLS = 30
# TASK_FASE3_NEXT §F follow-up, 2026-08-31: run 33442356029 (A1+A2, no crash) still took 2338.9s
# for duration_sec ~= items_fetched(1250) * 1.87s/item - every URL was fetched sequentially, one
# HTTP GET at a time. I/O-bound (network wait, not CPU), so threads give near-linear speedup
# without adding a dependency. 8 concurrent requests to the SAME host is well within normal
# browser/crawler etiquette.
# TASK_FASE4_CHIUSURA §1, 2026-09-01: il run 9d4f2a1 a 8 worker ha fatto crollare items_written
# 1055 -> 340 e la causa non e' stata isolata. Torna a 1: elimina la concorrenza come variabile
# non spiegata invece di tararla.
BACKFILL_FETCH_WORKERS = 1
BACKFILL_DAYS_DEFAULT = 30  # B1: 30 giorni di storia sulle fonti gia' validate, non piu' solo 7
BACKFILL_TARGET_DAYS = 7  # finestra che consideriamo "abbastanza": oltre questa il supplemento si spegne
# B2a/B1.2: dagli URL Wayback CDX vanno escluse le pagine indice/data/categoria/paginazione
# (es. "/2026/08/01/", "/page/2/", "/category/x/") e tenuti solo quelli con uno slug che sembra
# un vero articolo (parole-unite-da-trattini nell'ultimo segmento).
_INDEX_ONLY_PATH_RE = re.compile(r"/(\d{4}/\d{1,2}/\d{1,2}|page/\d+|category/[^/]+|tag/[^/]+|feed)/?$", re.I)
_ARTICLE_SLUG_RE = re.compile(r"[a-z0-9]{3,}-[a-z0-9-]{3,}", re.I)
_NON_ARTICLE_EXT_RE = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|pdf|css|js|ico|mp4|mp3|zip)(\?|$)", re.I)


def _looks_like_article_url(url):
    path = urlsplit(url).path
    if _NON_ARTICLE_EXT_RE.search(path):
        return False
    if _INDEX_ONLY_PATH_RE.search(path):
        return False
    return bool(_ARTICLE_SLUG_RE.search(path))

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = ROOT / "config" / "sources.yaml"
RAW_DIR = ROOT / "data" / "raw"
ERRORS_JSONL = ROOT / "data" / "errors.jsonl"


def load_sources():
    doc = miniyaml.load(SOURCES_YAML)
    return [s for s in doc.get("sources", []) if s.get("enabled", True)]


def log_error(kind, source_id, url, message, retry_count=0):
    ERRORS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "kind": kind, "source_id": source_id, "url": url, "message": str(message)[:500],
        "retry_count": retry_count,
    }
    with open(ERRORS_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def detect_script(text):
    return "cyrl" if has_cyrillic(text) else "latn"


def entry_text(entry):
    if entry.get("content"):
        html_val = entry["content"][0].get("value", "")
    else:
        html_val = entry.get("summary", "")
    return re.sub("<[^>]+>", " ", html_val).strip()


def collect_from_rss(source, window_start):
    items, errors = [], []
    try:
        status, _headers, body = fetch(source["feed_url"], timeout=15, retries=2)
    except FetchError as e:
        errors.append((e.kind, source["feed_url"], str(e)))
        return items, errors
    parsed = feedparser.parse(body)
    for entry in parsed.entries:
        url = entry.get("link")
        if not url:
            continue
        url = canonicalize_url(url)  # §5a: normalizza scheme/porta PRIMA del fetch, non dopo
        struct = entry.get("published_parsed") or entry.get("updated_parsed")
        published_at = None
        if struct:
            published_at = datetime(*struct[:6], tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
        elif entry.get("published"):
            published_at = parse_date_to_utc(entry.get("published"))
        if published_at:
            try:
                if datetime.fromisoformat(published_at.replace("Z", "+00:00")) < window_start:
                    continue
            except ValueError:
                pass
        text = entry_text(entry)
        final_url = url
        http_status = 200
        if len(text) < 400:  # feed senza fulltext: prova la pagina originale
            try:
                fstatus, _fh, fbody = fetch(url, timeout=15, retries=2)
                final_url = url
                http_status = fstatus
                page_text = trafilatura.extract(fbody.decode("utf-8", "ignore"), url=url) or ""
                if len(page_text) > len(text):
                    text = page_text
            except FetchError as e:
                errors.append((e.kind, url, str(e)))
        canonical = canonicalize_url(final_url)
        raw_id = sha256_hex(canonical)[:24]
        items.append({
            "raw_id": raw_id, "source_id": source["source_id"], "url": url, "final_url": canonical,
            "title": (entry.get("title") or "").strip(), "author": entry.get("author") or None,
            "text": text, "published_at": published_at,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "language": source.get("language", "sr"), "script": detect_script(text or entry.get("title", "")),
            "http_status": http_status, "content_hash": sha256_hex(text) if text else "",
        })
    return items, errors


def _parse_sitemap_xml(xml_bytes):
    """Protocollo sitemap standard (sitemaps.org), niente di specifico per testata. Ritorna
    ('sitemapindex'|'urlset', [(loc, lastmod|None), ...]).
    xml.etree non risolve entita' ESTERNE di default (fix upstream in expat da anni), ma resta
    vulnerabile a DoS da espansione di entita' interne ("billion laughs"): un DOCTYPE non serve
    mai in un sitemap.xml valido, quindi lo si rifiuta prima del parsing invece di aggiungere
    defusedxml come nuova dipendenza per due fonti fisse e note."""
    if b"<!DOCTYPE" in xml_bytes[:1000]:
        raise ET.ParseError("DOCTYPE non atteso in un sitemap.xml, rifiutato")
    root = ET.fromstring(xml_bytes)
    tag = root.tag.replace(_SITEMAP_NS, "")
    child_tag = "sitemap" if tag == "sitemapindex" else "url"
    entries = []
    for el in root.findall(f"{_SITEMAP_NS}{child_tag}"):
        loc = el.findtext(f"{_SITEMAP_NS}loc")
        lastmod = el.findtext(f"{_SITEMAP_NS}lastmod")
        if loc:
            entries.append((loc.strip(), (lastmod or "").strip() or None))
    return tag, entries


def collect_from_sitemap_backfill(source, window_start, exclude_canonical=None):
    """§4 — backfill SOLO da sitemap.xml, protocollo standard (index -> foglie -> url+lastmod).
    Nessun parser di paginazione su misura per fonte: se il sitemap non c'e' o non espone
    lastmod verificabili, si dichiara e si vive con l'accumulo (§4, punto 1).

    D0.2, TASK_BETA_03, 2026-08-28: `exclude_canonical` (URL canonici gia' raccolti) e' opzionale,
    None di default (comportamento invariato per il collect quotidiano, che deve sempre vedere gli
    URL piu' recenti del sitemap). Un secondo giro di backfill lo passa per saltare cio' che ha gia'
    - altrimenti MAX_BACKFILL_URLS riseleziona sempre la STESSA finestra (i piu' recenti), mai la
    storia successiva."""
    items, errors = [], []
    sitemap_url = source.get("sitemap_url") or (source.get("website_url", "").rstrip("/") + "/sitemap.xml")
    try:
        _status, _h, body = fetch(sitemap_url, timeout=15, retries=2)
    except FetchError as e:
        errors.append((e.kind, sitemap_url, str(e)))
        return items, errors
    try:
        kind, entries = _parse_sitemap_xml(body)
    except ET.ParseError as e:
        errors.append(("PARSE_ERROR", sitemap_url, str(e)))
        return items, errors

    if kind == "sitemapindex":
        dated = [(loc, parse_date_to_utc(lm) if lm else None) for loc, lm in entries]
        if any(d for _, d in dated):
            dated.sort(key=lambda x: x[1] or "", reverse=True)
            leaves = [loc for loc, _ in dated[:MAX_LEAF_SITEMAPS]]
        else:
            leaves = [loc for loc, _ in entries[-MAX_LEAF_SITEMAPS:]]  # nessun lastmod sull'indice: prova le ultime elencate
    else:
        leaves = [(sitemap_url, entries)]

    page_urls = []
    for leaf in leaves:
        if isinstance(leaf, tuple):
            leaf_url, leaf_entries = leaf
        else:
            leaf_url = leaf
            try:
                _s, _h, leaf_body = fetch(leaf_url, timeout=15, retries=2)
                _leaf_kind, leaf_entries = _parse_sitemap_xml(leaf_body)
            except (FetchError, ET.ParseError) as e:
                errors.append(("FETCH_ERROR", leaf_url, str(e)))
                continue
        for loc, lastmod in leaf_entries:
            dt_iso = parse_date_to_utc(lastmod) if lastmod else None
            if dt_iso is None:
                continue  # mai includere senza lastmod verificato: si scarterebbe copertura a caso
            if datetime.fromisoformat(dt_iso.replace("Z", "+00:00")) < window_start:
                continue
            if exclude_canonical and canonicalize_url(loc) in exclude_canonical:
                continue
            page_urls.append((loc, dt_iso))
        if len(page_urls) >= MAX_BACKFILL_URLS:
            break

    def _fetch_one(url_lastmod):
        url, lastmod = url_lastmod
        try:
            fstatus, _fh, fbody = fetch(url, timeout=15, retries=2)
        except FetchError as e:
            return ("error", (e.kind, url, str(e)))
        html_text = fbody.decode("utf-8", "ignore")
        text = trafilatura.extract(html_text, url=url) or ""
        meta = trafilatura.extract_metadata(html_text)
        title = (meta.title if meta else "") or ""
        canonical = canonicalize_url(url)
        raw_id = sha256_hex(canonical)[:24]
        return ("item", {
            "raw_id": raw_id, "source_id": source["source_id"], "url": url, "final_url": canonical,
            "title": title.strip(), "author": (meta.author if meta else None) or None,
            "text": text, "published_at": lastmod,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "language": source.get("language", "sr"), "script": detect_script(text or title),
            "http_status": fstatus, "content_hash": sha256_hex(text) if text else "",
        })

    with ThreadPoolExecutor(max_workers=BACKFILL_FETCH_WORKERS) as ex:
        for kind, payload in ex.map(_fetch_one, page_urls[:MAX_BACKFILL_URLS]):
            (items if kind == "item" else errors).append(payload)
    return items, errors


def _cdx_query(domain, date_from=None, date_to=None, limit=3000, timeout=45):
    """Una GET alla Wayback CDX API (pubblica, senza chiave). Verificato dal vivo (2026-08-28):
    query con 'from' E 'to' stretti su un intervallo recente possono dare 504 su alcuni domini
    (es. capital.ba) anche se il dominio stesso risponde in <2s — non e' un blocco dell'ambiente
    (confermato: web.archive.org/ e archive.org/ rispondono subito). La stessa query SENZA 'to'
    (o senza 'from') e' rapida: il filtro data va quindi applicato anche lato client come fallback."""
    params = f"url={domain}/*&output=json&fl=original,timestamp&collapse=urlkey&filter=statuscode:200&limit={limit}"
    if date_from:
        params += f"&from={date_from}"
    if date_to:
        params += f"&to={date_to}"
    url = f"https://web.archive.org/cdx/search/cdx?{params}"
    _status, _h, body = fetch(url, timeout=timeout, retries=0)
    try:
        data = json.loads(body) if body else []
    except json.JSONDecodeError as e:
        # verificato dal vivo, TASK_FASE4_CHIUSURA STEP 4, 2026-09-01 (run 33465875073): la CDX
        # API a volte tronca la risposta a meta' JSON (nessun errore HTTP, corpo troncato) -
        # json.loads() non e' un FetchError, quindi non veniva preso dagli except esistenti e
        # mandava in crash l'intero collect() su una fonte sola, stesso pattern del bug unicode
        # (commit 128713a).
        raise FetchError("FETCH_ERROR", f"CDX response non e' JSON valido: {e}") from e
    return data[1:] if data else []  # riga 0 e' l'header ["original","timestamp"]


def collect_from_wayback_cdx(source, window_start, window_end=None, cdx_timeout=40, cdx_fallback_timeout=60,
                              exclude_canonical=None):
    """§B1.2/§B2a — storia via Wayback CDX per le fonti senza sitemap (o il cui sitemap non copre
    30gg), e per recuperare Capital.ba (BLOCKED, 403 in diretta) e Dobojski.info (MANUAL_ONLY,
    nessun sitemap). Il testo si prende da trafilatura sull'URL vivo; solo se fallisce, dalla
    replay Wayback (mai l'unica via per le fonti raggiungibili in diretta). Timeout piu' stretti
    (usati dal supplemento B1 su piu' fonti) accettano meno copertura pur di non bloccare a lungo
    su una singola fonte lenta — il recupero mirato di B2a usa i default, piu' pazienti."""
    items, errors = [], []
    domain = urlsplit(source.get("website_url") or "").netloc
    if not domain:
        return items, [("PARSE_ERROR", "", "nessun website_url per la query CDX")]
    date_from = window_start.strftime("%Y%m%d")
    date_to = (window_end or datetime.now(timezone.utc)).strftime("%Y%m%d")

    try:
        rows = _cdx_query(domain, date_from, date_to, timeout=cdx_timeout)
    except FetchError:
        # fallback: verificato dal vivo (2026-08-28) che alcuni domini (es. capital.ba) danno
        # timeout/504 SOLO quando 'from' e' stretto e recente, ma rispondono (lenti, ~15-50s) a
        # un 'from' largo (inizio anno) SENZA 'to' — filtrato poi lato client sulla finestra vera.
        wide_from = window_start.replace(month=1, day=1).strftime("%Y%m%d")
        try:
            rows = _cdx_query(domain, date_from=wide_from, limit=5000, timeout=cdx_fallback_timeout)
            rows = [r for r in rows if r[1] >= date_from]
        except FetchError as e:
            errors.append((e.kind, domain, str(e)))
            return items, errors

    seen_canonical = set()
    candidates = []
    for original, ts in rows:
        if not _looks_like_article_url(original):
            continue
        canon = canonicalize_url(original)
        if canon in seen_canonical:
            continue
        seen_canonical.add(canon)
        if exclude_canonical and canon in exclude_canonical:
            continue
        candidates.append((original, ts))

    def _fetch_one(original_ts):
        original, ts = original_ts
        html_text, http_status, via_wayback = None, None, False
        try:
            fstatus, _fh, fbody = fetch(original, timeout=15, retries=1)
            html_text, http_status = fbody.decode("utf-8", "ignore"), fstatus
        except FetchError:
            pass
        if not html_text or len(html_text) < 500:
            wb_url = f"https://web.archive.org/web/{ts}/{original}"
            try:
                fstatus, _fh, fbody = fetch(wb_url, timeout=20, retries=1)
                html_text, http_status, via_wayback = fbody.decode("utf-8", "ignore"), fstatus, True
            except FetchError as e:
                return ("error", (e.kind, original, str(e)))
        text = trafilatura.extract(html_text, url=original) or ""
        if len(text) < 200:
            return ("skip", None)
        meta = trafilatura.extract_metadata(html_text)
        title = (meta.title if meta else "") or ""
        if not title.strip():
            return ("skip", None)  # nessun titolo estratto: pagina non-articolo sfuggita al filtro URL
        published = parse_date_to_utc(getattr(meta, "date", None)) if meta and getattr(meta, "date", None) else None
        if not published:
            # ts e' il momento dell'ARCHIVIAZIONE, non della pubblicazione: usato solo come ultima
            # istanza (l'articolo e' sempre stato pubblicato prima di essere archiviato, mai dopo).
            try:
                published = datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                published = None
        canonical = canonicalize_url(original)
        raw_id = sha256_hex(canonical)[:24]
        return ("item", {
            "raw_id": raw_id, "source_id": source["source_id"], "url": original, "final_url": canonical,
            "title": title.strip(), "author": (meta.author if meta else None) or None,
            "text": text, "published_at": published,
            "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "language": source.get("language", "sr"), "script": detect_script(text or title),
            "http_status": http_status, "content_hash": sha256_hex(text) if text else "",
            "via_wayback": via_wayback,
        })

    with ThreadPoolExecutor(max_workers=BACKFILL_FETCH_WORKERS) as ex:
        for kind, payload in ex.map(_fetch_one, candidates[:MAX_BACKFILL_URLS]):
            if kind == "item":
                items.append(payload)
            elif kind == "error":
                errors.append(payload)
    return items, errors


def collect_from_html_source(source, window_start, exclude_canonical=None):
    """Fonti fetch_mode 'html': backfill da sitemap.xml se il metodo lo dichiara ('sitemap' nel
    campo method), Wayback CDX se dichiara 'wayback', altrimenti MANUAL_ONLY dichiarato — niente
    parser di paginazione su misura (§4, punto 1: gli archivi HTML cambiano struttura, la
    manutenzione ricade su una persona sola)."""
    method = source.get("method") or ""
    if "sitemap" in method:
        return collect_from_sitemap_backfill(source, window_start, exclude_canonical=exclude_canonical)
    if "wayback" in method:
        return collect_from_wayback_cdx(source, window_start, exclude_canonical=exclude_canonical)
    return [], [("PARSE_ERROR", source.get("website_url", ""),
                 "MANUAL_ONLY: nessun sitemap.xml stabile verificato per questa fonte (§4/§5b), "
                 "nessun parser di paginazione su misura per policy del task")]


def collect_supplemental_history(source, window_start, exclude_canonical=None):
    """B1 — storia oltre l'orizzonte del feed RSS, per le fonti il cui fetch_mode primario e'
    'rss' (quindi non gia' coperte da sitemap/wayback come metodo principale). Sitemap provato
    SILENZIOSAMENTE (assente = normale per la maggior parte delle fonti, non un errore da
    loggare); Wayback CDX solo se il sitemap non c'e' o non ha dato nulla nella finestra, con
    timeout piu' stretti che in B2a: qui e' un supplemento su piu' fonti, non un recupero
    mirato — se una fonte e' lenta si passa oltre, non si insiste (stesso principio del task
    per GDELT: 'non insistere')."""
    website = source.get("website_url") or ""
    if not website:
        return [], []
    sitemap_url = website.rstrip("/") + "/sitemap.xml"
    try:
        fetch(sitemap_url, timeout=8, retries=0)
        has_sitemap = True
    except FetchError:
        has_sitemap = False

    if has_sitemap:
        sm_items, sm_errors = collect_from_sitemap_backfill(source, window_start, exclude_canonical=exclude_canonical)
        if sm_items:
            return sm_items, sm_errors

    try:
        wb_items, wb_errors = collect_from_wayback_cdx(source, window_start, cdx_timeout=15, cdx_fallback_timeout=25,
                                                        exclude_canonical=exclude_canonical)
    except FetchError as e:
        return [], [(e.kind, website, str(e))]
    return wb_items, wb_errors


def compute_window_actual_days():
    """§4, punto 2 — giorni civili UTC distinti REALMENTE coperti da ogni fonte, letti da tutti
    i data/raw/*.jsonl accumulati. Mai '7 giorni' scritto per default: si misura."""
    from pilot.clean import out_of_window  # import locale: collect e' importato da clean nei test

    days_by_source = {}
    for path in RAW_DIR.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            it = json.loads(line)
            pub = it.get("published_at")
            if not pub:
                continue
            # stesso scarto di clean.py: le pagine non-articolo prese via sitemap portano il
            # lastmod come published_at e gonfiavano questo conteggio (BL_IJ3_002: 34 giorni su
            # una finestra di 30). Senza questo guard sources.yaml resta sporco anche dopo il
            # filtro nel clean, perche' qui si legge data/raw, non data/clean.jsonl.
            if out_of_window(pub, it.get("scraped_at")):
                continue
            try:
                d = datetime.fromisoformat(pub.replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                continue
            days_by_source.setdefault(it["source_id"], set()).add(d)
    return {sid: len(days) for sid, days in days_by_source.items()}


def write_window_actual_days(window_by_source):
    """Aggiorna (o inserisce) la riga window_actual_days per ogni fonte in config/sources.yaml,
    per sostituzione testuale mirata: preserva commenti e formattazione del file esistente."""
    text = SOURCES_YAML.read_text(encoding="utf-8")
    lines = text.split("\n")
    out = []
    current_sid = None
    for line in lines:
        m = re.match(r"\s*- source_id:\s*(\S+)", line)
        if m:
            current_sid = m.group(1)
        if re.match(r"\s*window_actual_days:", line):
            continue  # rimossa, riscritta subito dopo items_7d_at_audit
        out.append(line)
        if current_sid and re.match(r"\s*items_7d_at_audit:", line):
            indent = line[: len(line) - len(line.lstrip())]
            n = window_by_source.get(current_sid, 0)
            out.append(f"{indent}window_actual_days: {n}")
    SOURCES_YAML.write_text("\n".join(out), encoding="utf-8", newline="\n")


def _needs_history_supplement(source, days):
    """TASK_FASE2_COMPLETAMENTO §A1: salta il supplemento (wayback/sitemap, fino a
    MAX_BACKFILL_URLS fetch) se la fonte ha gia' `window_actual_days` (calcolato sull'ultimo
    run da compute_window_actual_days) >= alla finestra richiesta. Senza questo, ogni run
    rifaceva il supplemento per ogni fonte RSS a prescindere, anche quando il dedup in
    scrittura li avrebbe scartati comunque (~50min anziche' pochi minuti su un run gia' pieno)."""
    return source.get("window_actual_days", 0) < days


def collect(days=BACKFILL_DAYS_DEFAULT, supplement_history=True, only_source_ids=None):
    """`only_source_ids` (opzionale): raccoglie solo queste fonti invece di tutte le abilitate —
    usato da `pilot/run_monitor.py` (config/monitoring.yaml) per rispettare frequenze diverse per
    target senza duplicare il fetch della stessa fonte in piu' target nella stessa esecuzione.
    None (default) = comportamento invariato, tutte le fonti abilitate."""
    sources = load_sources()
    if only_source_ids is not None:
        sources = [s for s in sources if s["source_id"] in only_source_ids]
    window_start = datetime.now(timezone.utc) - timedelta(days=days)

    # TASK_FASE3_NEXT §F (A2): stessa scansione di data/raw/*.jsonl gia' fatta comunque per il
    # dedup in scrittura (misurata 0.52s su 1808 righe) - anticipata qui per riuso, non ripetuta.
    # existing_canonicals alimenta exclude_canonical del supplemento: senza, ogni run rifaceva
    # fino a MAX_BACKFILL_URLS fetch per fonte, riselezionando sempre la stessa finestra recente
    # del sitemap/CDX invece di avanzare nella storia.
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    existing_ids = set()
    existing_canonicals = set()
    for path in RAW_DIR.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            existing_ids.add(rec["raw_id"])
            if rec.get("final_url"):
                existing_canonicals.add(rec["final_url"])

    all_items = []
    per_source_counts = {}
    for source in sources:
        sid = source["source_id"]
        is_rss = source.get("fetch_mode") == "rss" and source.get("feed_url")
        try:
            if is_rss:
                items, errors = collect_from_rss(source, window_start)
            else:
                items, errors = collect_from_html_source(source, window_start)

            # B1: il feed RSS copre poche decine di entry recenti, non 30 giorni. Supplemento
            # silenzioso (sitemap se c'e', altrimenti Wayback CDX) SOLO per le fonti rss-primarie:
            # le altre gia' usano sitemap/wayback come metodo principale, non serve raddoppiare.
            # A1 (window_actual_days) e A2 (exclude_canonical) sono complementari, non alternative:
            # A1 salta del tutto le fonti gia' piene, A2 fa avanzare le altre invece di ripetersi.
            if is_rss and supplement_history and _needs_history_supplement(source, BACKFILL_TARGET_DAYS):
                sup_items, sup_errors = collect_supplemental_history(source, window_start,
                                                                       exclude_canonical=existing_canonicals)
                existing_urls = {it["raw_id"] for it in items}
                items = items + [it for it in sup_items if it["raw_id"] not in existing_urls]
                errors = errors + sup_errors
        except Exception as e:
            # TASK_FASE4_CHIUSURA STEP 4, 2026-09-01 (run 33465875073): un'eccezione non prevista
            # su UNA fonte (finora visto: UnicodeEncodeError da un URL sitemap, JSONDecodeError da
            # una risposta CDX troncata) mandava in crash l'intero collect(), su tutte le fonti
            # gia' raccolte in quel run - contro il contratto dichiarato dal modulo (vedi docstring
            # in cima al file: "una fonte rotta non blocca le altre"). Guardia qui, non nel singolo
            # punto che ha fatto scoprire il bug: root cause e' "una fonte puo' fallire in modi non
            # ancora visti", non lo specifico tipo di eccezione.
            url = source.get("website_url") or source.get("feed_url") or ""
            items, errors = [], [("FETCH_ERROR", url, f"{type(e).__name__}: {e}")]

        per_source_counts[sid] = len(items)
        all_items.extend(items)
        for kind, url, msg in errors:
            log_error(kind, sid, url, msg)
        print(f"{sid:16s} -> {len(items):4d} item, {len(errors)} errori")

    out_path = RAW_DIR / f"{datetime.now(timezone.utc).date().isoformat()}.jsonl"
    # dedup contro TUTTI i raw/*.jsonl (non solo il file di oggi): collect gira piu' volte al
    # giorno e su piu' giorni durante l'accumulo, e un raw_id gia' scritto ieri non va riscritto oggi.
    with open(out_path, "a", encoding="utf-8") as f:
        written = 0
        for item in all_items:
            if item["raw_id"] in existing_ids:
                continue
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            existing_ids.add(item["raw_id"])
            written += 1
    print(f"\nTotale item raccolti: {len(all_items)} | nuovi scritti in {out_path.name}: {written}")
    print(f"Per fonte: {per_source_counts}")

    window_by_source = compute_window_actual_days()
    write_window_actual_days(window_by_source)
    print(f"window_actual_days aggiornato in config/sources.yaml: {window_by_source}")

    return all_items, per_source_counts, written


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=BACKFILL_DAYS_DEFAULT)
    args = ap.parse_args()
    collect(days=args.days)


if __name__ == "__main__":
    main()
