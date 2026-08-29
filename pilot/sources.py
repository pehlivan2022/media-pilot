"""Audit fonti reale (§1): un fetch HTTP per candidato, in ordine RSS -> sitemap -> HTML.

Scrive docs/SOURCE_AUDIT.csv per OGNI candidato provato e config/sources.yaml con le sole
righe READY_*. Nessun READY_* senza un fetch riuscito.
"""
import csv
import json
import re
import socket
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import feedparser
import trafilatura

from pilot.util import USER_AGENT, FetchError, fetch

ROOT = Path(__file__).resolve().parent.parent
CSV_CANDIDATES = Path(r"C:\Users\frontofficedx\Desktop\NIK 2026\IZVORI_MASTER_media-pilot_FINAL-sa-sugestijama.csv")
SOURCE_AUDIT_CSV = ROOT / "docs" / "SOURCE_AUDIT.csv"
SOURCES_YAML = ROOT / "config" / "sources.yaml"

MAX_TRIED = 200  # §5b: nessuna quota sui candidati READY — "fermarsi a 10" era l'istruzione sbagliata
FEED_PATHS = ["/rss", "/feed", "/rss.xml", "/atom.xml", "/feed/"]
SITEMAP_PATHS = ["/sitemap.xml", "/sitemap_index.xml"]
HTTP_TIMEOUT = 15
NOW = datetime.now(timezone.utc)
WINDOW_7D = NOW - timedelta(days=7)



def load_tier1():
    with open(CSV_CANDIDATES, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    tier1 = [r for r in rows if (r.get("priority_tier") or "").strip() == "1"]
    tier1.sort(key=lambda r: -_num(r.get("election_relevance")))
    return tier1


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def find_feed_link(html_text, base_url):
    m = re.search(
        r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
        html_text, re.I,
    )
    if not m:
        m = re.search(
            r'<link[^>]+href=["\']([^"\']+)["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\']',
            html_text, re.I,
        )
    return urljoin(base_url, m.group(1)) if m else None


def looks_like_feed(body_bytes):
    head = body_bytes[:200].lstrip().lower()
    return head.startswith(b"<?xml") or b"<rss" in head or b"<feed" in head


def count_recent_entries(parsed_feed):
    recent = 0
    fulltext_hits = 0
    total = 0
    for entry in parsed_feed.entries:
        total += 1
        struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if struct:
            dt = datetime(*struct[:6], tzinfo=timezone.utc)
            if dt >= WINDOW_7D:
                recent += 1
        body = entry.get("content", [{}])[0].get("value") if entry.get("content") else entry.get("summary", "")
        if body and len(re.sub("<[^>]+>", "", body)) > 500:
            fulltext_hits += 1
    fulltext = fulltext_hits >= max(1, total // 2) if total else False
    return recent, fulltext


def try_feed(base_url, home_html):
    candidates = []
    link = find_feed_link(home_html, base_url) if home_html else None
    if link:
        candidates.append(link)
    for path in FEED_PATHS:
        candidates.append(urljoin(base_url, path))
    seen = set()
    for feed_url in candidates:
        if feed_url in seen:
            continue
        seen.add(feed_url)
        try:
            status, _headers, body = fetch(feed_url, timeout=HTTP_TIMEOUT)
        except FetchError:
            continue
        if status != 200 or not looks_like_feed(body):
            continue
        parsed = feedparser.parse(body)
        if not parsed.entries:
            continue
        recent, fulltext = count_recent_entries(parsed)
        return {"feed_url": feed_url, "items_7d": recent, "fulltext": fulltext, "total_entries": len(parsed.entries)}
    return None


def try_sitemap(base_url):
    for path in SITEMAP_PATHS:
        url = urljoin(base_url, path)
        try:
            status, _headers, body = fetch(url, timeout=HTTP_TIMEOUT)
        except FetchError:
            continue
        if status != 200:
            continue
        lastmods = re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", body.decode("utf-8", "ignore"))
        recent_urls = []
        for loc, lastmod in lastmods:
            try:
                dt = datetime.fromisoformat(lastmod.strip().replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= WINDOW_7D:
                    recent_urls.append(loc)
            except ValueError:
                continue
        if recent_urls:
            return {"sitemap_url": url, "recent_urls": recent_urls[:10]}
    return None


def robots_allows(base_url, path="/"):
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urljoin(base_url, "/robots.txt"))
    try:
        status, _headers, body = fetch(urljoin(base_url, "/robots.txt"), timeout=HTTP_TIMEOUT)
        if status == 200:
            rp.parse(body.decode("utf-8", "ignore").splitlines())
        else:
            return True  # nessun robots.txt -> nessun divieto dichiarato
    except FetchError:
        return True
    try:
        return rp.can_fetch(USER_AGENT, urljoin(base_url, path))
    except Exception:
        return True


def try_html_from_urls(urls, robots_ok):
    if not robots_ok or not urls:
        return None
    recent = 0
    checked = 0
    for url in urls[:8]:
        try:
            status, _headers, body = fetch(url, timeout=HTTP_TIMEOUT)
        except FetchError:
            continue
        checked += 1
        html_text = body.decode("utf-8", "ignore")
        extracted = trafilatura.extract(html_text, with_metadata=True, favor_precision=True, url=url)
        if not extracted or len(extracted) < 200:
            continue  # non server-rendered o pagina vuota senza JS
        meta = trafilatura.extract_metadata(html_text)
        pub = getattr(meta, "date", None) if meta else None
        if pub:
            try:
                dt = datetime.fromisoformat(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= WINDOW_7D:
                    recent += 1
            except ValueError:
                pass
    if checked == 0:
        return None
    return {"items_7d": recent, "checked": checked, "server_rendered": True}


def audit_one(row):
    source_id = row["source_id"]
    name = row["naziv_izvora"]
    url = (row.get("website_url") or "").strip()
    result = {
        "source_id": source_id, "name": name, "url": url, "feed_url": "",
        "method": "", "items_7d": 0, "fulltext_in_feed": "", "robots_ok": "",
        "stato": "TO_VERIFY", "checked_at": NOW.isoformat().replace("+00:00", "Z"), "note": "",
    }
    if not url:
        result["stato"] = "NOT_USEFUL"
        result["note"] = "nessun website_url nel registry (solo social/persona)"
        return result

    try:
        status, _headers, body = fetch(url, timeout=HTTP_TIMEOUT)
    except FetchError as e:
        result["stato"] = "BLOCKED" if e.kind in ("BLOCKED", "RATE_LIMIT") else "TO_VERIFY"
        result["note"] = f"{e.kind}: {e}"
        return result
    home_html = body.decode("utf-8", "ignore")

    feed_res = try_feed(url, home_html)
    if feed_res and feed_res["items_7d"] >= 1:
        result.update({
            "feed_url": feed_res["feed_url"], "method": "rss", "items_7d": feed_res["items_7d"],
            "fulltext_in_feed": feed_res["fulltext"], "robots_ok": True, "stato": "READY_RSS",
            "note": f"{feed_res['total_entries']} entry totali nel feed",
        })
        return result
    if feed_res:
        result["note"] = f"feed trovato ma 0 item negli ultimi 7g (tot {feed_res['total_entries']})"

    robots_ok = robots_allows(url)
    result["robots_ok"] = robots_ok

    sm = try_sitemap(url)
    if sm and robots_ok:
        html_res = try_html_from_urls(sm["recent_urls"], robots_ok)
        if html_res and html_res["items_7d"] >= 1:
            result.update({
                "method": "sitemap+html", "items_7d": html_res["items_7d"], "fulltext_in_feed": False,
                "stato": "READY_HTML",
                "note": f"sitemap {sm['sitemap_url']}, {html_res['checked']} articoli controllati",
            })
            return result

    # fallback: link della homepage verso lo stesso dominio, come ultima istanza del metodo 4
    if robots_ok:
        domain = urlsplit(url).netloc
        links = re.findall(r'href=["\'](https?://[^"\']+|/[^"\']+)["\']', home_html)
        same_domain = []
        for href in links:
            full = urljoin(url, href)
            if urlsplit(full).netloc == domain and re.search(r"/\d{2,4}[/-]|[a-z]{3,}-[a-z0-9-]{5,}", full):
                same_domain.append(full)
        same_domain = list(dict.fromkeys(same_domain))
        html_res = try_html_from_urls(same_domain, robots_ok)
        if html_res and html_res["items_7d"] >= 1:
            result.update({
                "method": "html_home_links", "items_7d": html_res["items_7d"], "fulltext_in_feed": False,
                "stato": "READY_HTML",
                "note": f"{html_res['checked']} articoli controllati dai link homepage",
            })
            return result
        if html_res:
            result["note"] = (result["note"] + f"; html controllato, 0 recenti su {html_res['checked']}").strip("; ")
        elif not result["note"]:
            result["note"] = "nessun testo estraibile senza JS (probabile SPA)"

    if not robots_ok:
        result["stato"] = "BLOCKED"
        result["note"] = "robots.txt nega l'accesso alla sezione utile"
    elif not result["note"]:
        result["stato"] = "NOT_USEFUL"
        result["note"] = "nessun item negli ultimi 7 giorni con i metodi disponibili"
    else:
        result["stato"] = "NOT_USEFUL"
    return result


def write_audit_csv(results):
    SOURCE_AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_id", "name", "url", "feed_url", "method", "items_7d", "fulltext_in_feed",
              "robots_ok", "stato", "checked_at", "note"]
    with open(SOURCE_AUDIT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in results:
            w.writerow({k: r.get(k, "") for k in fields})


def guess_language_script(row):
    return "sr", "cyrl" if "cirilic" in (row.get("napomena") or "").lower() else "latn"


def source_type_for(row):
    """tip_izvora del registry, cosi' com'e' (§G.3: source_type viene dalla colonna del registry,
    non da una mappa inventata). menu (news/local/institutions/campaign) si deriva da questo in score.py."""
    return row.get("tip_izvora") or "unknown"


def write_sources_yaml(results, rows_by_id):
    ready = [r for r in results if r["stato"] in ("READY_RSS", "READY_HTML")]
    lines = [
        "# generato da pilot/sources.py — solo righe con fetch riuscito (READY_RSS / READY_HTML).",
        f"# audit completo: docs/SOURCE_AUDIT.csv ({len(results)} candidati provati)",
        "sources:",
    ]
    for r in ready:
        row = rows_by_id.get(r["source_id"], {})
        lines.append(f"  - source_id: {r['source_id']}")
        lines.append(f"    name: {json.dumps(r['name'], ensure_ascii=False)}")
        lines.append(f"    feed_url: {json.dumps(r['feed_url']) if r['feed_url'] else 'null'}")
        lines.append(f"    fetch_mode: {'rss' if r['stato'] == 'READY_RSS' else 'html'}")
        lines.append(f"    method: {r['method']}")
        lines.append("    language: sr")
        lines.append(f"    script: {'cyrl' if row.get('napomena', '') else 'latn'}")
        lines.append(f"    source_type: {source_type_for(row)}")
        lines.append("    owner_group: null  # non verificato, vedi napomena registry")
        lines.append(f"    territory: {json.dumps(row.get('izborna_jedinica') or 'ALL')}")
        lines.append("    enabled: true")
        lines.append(f"    last_verified_at: {json.dumps(r['checked_at'])}")
        lines.append(f"    items_7d_at_audit: {r['items_7d']}")
        lines.append(f"    website_url: {json.dumps(r['url'])}")
    lines.append(f"count: {len(ready)}")
    SOURCES_YAML.parent.mkdir(parents=True, exist_ok=True)
    SOURCES_YAML.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return ready


def main():
    tier1 = load_tier1()
    rows_by_id = {r["source_id"]: r for r in tier1}
    results = []
    for row in tier1[:MAX_TRIED]:
        res = audit_one(row)
        results.append(res)
        print(f"{res['source_id']:16s} {res['stato']:10s} {res['method']:14s} items_7d={res['items_7d']:<3} {res['name']}")
    write_audit_csv(results)
    ready = write_sources_yaml(results, rows_by_id)
    print(f"\nProvati: {len(results)} | READY: {len(ready)} (nessuna quota, tutti i candidati tier-1 provati)")
    return results, ready


if __name__ == "__main__":
    main()
