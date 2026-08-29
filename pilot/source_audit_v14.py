"""TASK_SOURCE_EXPANSION_DAILY_PILOT_01 — audit dei 110 candidati v14 contro sources.yaml attuale.

Non tocca config/sources.yaml (scrive solo un frammento proposto in scratchpad) ne' i file
pipeline vietati dal task. Riusa gli helper HTTP di pilot/sources.py (try_feed/try_sitemap/
robots_allows/try_html_from_urls) invece di reimplementarli.

Ordine di test per candidato: RSS -> sitemap+HTML -> homepage-link HTML (solo come segnale,
mai promosso da solo: pilot/collect.py collect_from_html_source non sa raccogliere un metodo
'html_home_links', solo 'sitemap'/'wayback' nel campo method — vedi nota in decision/notes).
"""
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd

from pilot import miniyaml
from pilot.sources import find_feed_link, robots_allows, try_feed, try_html_from_urls, try_sitemap
from pilot.util import FetchError, fetch

ROOT = Path(__file__).resolve().parent.parent
V14_XLSX = ROOT / "input" / "source_candidates" / "media_pilot_fonti_facebook_aggiornate_v14.xlsx"
SOURCES_YAML = ROOT / "config" / "sources.yaml"
AUDIT_CSV = ROOT / "docs" / "SOURCE_EXPANSION_AUDIT_01.csv"
PROBLEMS_CSV = ROOT / "docs" / "SOURCE_PROBLEMS_01.csv"
SCRATCH_PROPOSED = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "proposed_sources_fragment.yaml"

HTTP_TIMEOUT = 15
NOW = datetime.now(timezone.utc)


def canon_domain(u):
    if not isinstance(u, str) or not u.strip():
        return ""
    u = u.strip()
    if not re.match(r"^https?://", u):
        u = "http://" + u
    netloc = urlsplit(u).netloc.lower()
    return re.sub(r"^www\.", "", netloc)


def load_active():
    doc = miniyaml.load(SOURCES_YAML)
    sources = doc.get("sources", [])
    by_domain = {}
    by_id = {}
    for s in sources:
        d = canon_domain(s.get("website_url"))
        if d:
            by_domain[d] = s["source_id"]
        by_id[s["source_id"]] = d
    return by_domain, by_id


def is_institutional(macro_tipo):
    mt = (macro_tipo or "").upper()
    return any(k in mt for k in ("PARTIJE", "IZBORI", "EKONOMIJA"))


def classify(url, macro_tipo):
    """Ritorna un dict con test_status/fetch_method_found/feed_url/http_status/items_recent/
    valid_articles/fulltext_ok/date_ok/problem/notes secondo il vocabolario status del task."""
    out = {
        "test_status": "", "fetch_method_found": "none", "feed_url": "", "http_status": "",
        "items_recent": 0, "valid_articles": 0, "fulltext_ok": False, "date_ok": False,
        "problem": "", "notes": "",
    }
    try:
        status, _h, body = fetch(url, timeout=HTTP_TIMEOUT)
    except FetchError as e:
        out["http_status"] = e.http_status or ""
        msg = str(e).lower()
        if e.kind == "BLOCKED":
            out["test_status"] = "BLOCKED_403"
        elif e.kind == "RATE_LIMIT":
            out["test_status"] = "BLOCKED_429"
        elif "ssl" in msg or "certificate" in msg:
            out["test_status"] = "SSL_ERROR"
        elif "timed out" in msg or "timeout" in msg:
            out["test_status"] = "TIMEOUT"
        else:
            out["test_status"] = "DEAD_DOMAIN"
        out["problem"] = out["test_status"]
        out["notes"] = str(e)[:300]
        return out

    out["http_status"] = status
    home_html = body.decode("utf-8", "ignore")

    # 1) RSS
    feed_res = try_feed(url, home_html)
    if feed_res and feed_res["items_7d"] >= 1:
        out.update({
            "test_status": "READY_RSS", "fetch_method_found": "rss", "feed_url": feed_res["feed_url"],
            "items_recent": feed_res["items_7d"], "valid_articles": feed_res["items_7d"],
            "fulltext_ok": bool(feed_res["fulltext"]), "date_ok": True,
            "notes": f"{feed_res['total_entries']} entry totali nel feed",
        })
        return out
    feed_found_empty = bool(feed_res)

    # robots
    robots_ok = robots_allows(url)
    if not robots_ok:
        out["test_status"] = "ROBOTS_RESTRICTED"
        out["problem"] = "ROBOTS_RESTRICTED"
        out["notes"] = "robots.txt nega l'accesso"
        return out

    # 2) sitemap + html
    sm = try_sitemap(url)
    if sm:
        html_res = try_html_from_urls(sm["recent_urls"], robots_ok)
        if html_res and html_res["items_7d"] >= 1:
            out.update({
                "test_status": "READY_SITEMAP", "fetch_method_found": "sitemap",
                "items_recent": html_res["items_7d"], "valid_articles": html_res["checked"],
                "fulltext_ok": True, "date_ok": True,
                "notes": f"sitemap {sm['sitemap_url']}, {html_res['checked']} articoli controllati",
            })
            return out
        if html_res:
            out["notes"] = f"sitemap trovato ma 0 articoli recenti su {html_res['checked']} controllati"

    # 3) homepage article links (solo segnale — pilot/collect.py non sa raccoglierlo da solo)
    domain = urlsplit(url).netloc
    links = re.findall(r'href=["\'](https?://[^"\']+|/[^"\']+)["\']', home_html)
    same_domain = []
    for href in links:
        full = href if href.startswith("http") else f"{urlsplit(url).scheme}://{domain}{href}"
        if urlsplit(full).netloc == domain and re.search(r"/\d{2,4}[/-]|[a-z]{3,}-[a-z0-9-]{5,}", full):
            same_domain.append(full)
    same_domain = list(dict.fromkeys(same_domain))
    html_res = try_html_from_urls(same_domain, robots_ok)
    if html_res and html_res["items_7d"] >= 1:
        out.update({
            "test_status": "READY_HTML", "fetch_method_found": "html_home_links",
            "items_recent": html_res["items_7d"], "valid_articles": html_res["checked"],
            "fulltext_ok": True, "date_ok": True,
            "notes": (f"{html_res['checked']} articoli controllati dai link homepage; "
                      "ATTENZIONE: pilot/collect.py collect_from_html_source non raccoglie un "
                      "metodo che non sia 'sitemap'/'wayback' nel campo method -> non promuovibile "
                      "senza sitemap/wayback confermati (vedi decision)."),
        })
        return out

    if feed_found_empty:
        out["test_status"] = "NO_RSS"
        out["problem"] = "RSS_EMPTY"
        out["notes"] = "feed trovato ma 0 item negli ultimi 7g"
    elif html_res:
        out["test_status"] = "NO_ARTICLE_LINKS"
        out["problem"] = "NO_ARTICLE_LINKS"
        out["notes"] = f"html controllato, 0 articoli recenti su {html_res['checked']}"
    else:
        out["test_status"] = "JS_ONLY"
        out["problem"] = "JS_ONLY"
        out["notes"] = "nessun testo estraibile senza JS (probabile SPA) e nessun feed/sitemap utile"
    return out


def rank_key(row):
    tier = int(row.get("priority_tier") or 9)
    doboj = float(row.get("doboj_relevance") or 0)
    ij = str(row.get("ij") or "")
    ij_bonus = 1.0 if ("IJ5" in ij or "IJ3" in ij) else 0.0
    elec = float(row.get("election_relevance") or 0)
    inst = 1.0 if is_institutional(row.get("macro_tipo")) else 0.0
    tech = float(row.get("technical_access") or 0)
    return (tier, -doboj, -ij_bonus, -elec, -inst, -tech)


def main():
    df = pd.ExcelFile(V14_XLSX).parse("01_MASTER_ALL")
    df["canon_domain"] = df["website_url"].apply(canon_domain)
    active_by_domain, active_by_id = load_active()

    rows = df.to_dict("records")
    for r in rows:
        r["already_active"] = r["canon_domain"] in active_by_domain and r["canon_domain"] != ""
        r["current_source_id"] = active_by_domain.get(r["canon_domain"], "")
        r["id_conflict"] = (
            r["source_id"] in active_by_id
            and not r["already_active"]
        )

    has_url = [r for r in rows if isinstance(r.get("website_url"), str) and r["website_url"].strip()]
    no_url = [r for r in rows if r not in has_url]
    not_active = [r for r in has_url if not r["already_active"]]

    tier1_gap = [r for r in not_active if int(r.get("priority_tier") or 0) == 1]
    tier2_all = [r for r in not_active if int(r.get("priority_tier") or 0) == 2]
    tier3_all = [r for r in not_active if int(r.get("priority_tier") or 0) == 3]

    def relevant_tier2(r):
        mt = str(r.get("macro_tipo") or "").upper()
        ij = str(r.get("ij") or "").upper()
        doboj = float(r.get("doboj_relevance") or 0)
        elec = float(r.get("election_relevance") or 0)
        return (
            doboj >= 0.4 or "IJ5" in ij or "IJ3" in ij or "PARTIJE" in mt or "POL" in mt
            or "IZBORI" in mt or "EKONOMIJA" in mt or elec >= 0.6
        )

    tier2_targeted = sorted([r for r in tier2_all if relevant_tier2(r)], key=rank_key)
    tier1_gap = sorted(tier1_gap, key=rank_key)

    tested_ids = set()
    results_by_id = {}

    def run_test(r):
        sid = r["source_id"]
        if sid in tested_ids:
            return
        tested_ids.add(sid)
        url = r["website_url"].strip()
        print(f"testing {sid:16s} tier={r.get('priority_tier')} {url}", flush=True)
        res = classify(url, r.get("macro_tipo"))
        results_by_id[sid] = res
        print(f"  -> {res['test_status']:20s} method={res['fetch_method_found']:16s} items_recent={res['items_recent']}", flush=True)

    for r in tier1_gap:
        run_test(r)
    for r in tier2_targeted:
        run_test(r)

    # Tier 3: nessun fetch di default (budget/policy) — righe presenti nell'audit ma non testate.
    for r in tier3_all:
        results_by_id.setdefault(r["source_id"], {
            "test_status": "", "fetch_method_found": "", "feed_url": "", "http_status": "",
            "items_recent": "", "valid_articles": "", "fulltext_ok": "", "date_ok": "",
            "problem": "", "notes": "NOT_TESTED: tier 3, nessun gap geografico/tematico residuo identificato dopo tier 1+2 — budget di fetch non speso per policy §8/§15.",
        })

    # righe attive e senza url: nessun fetch
    for r in rows:
        sid = r["source_id"]
        if sid in results_by_id:
            continue
        if r["already_active"]:
            results_by_id[sid] = {
                "test_status": "ALREADY_ACTIVE", "fetch_method_found": "", "feed_url": "",
                "http_status": "", "items_recent": "", "valid_articles": "", "fulltext_ok": "",
                "date_ok": "", "problem": "", "notes": f"gia' attiva come {r['current_source_id']}",
            }
        elif not (isinstance(r.get("website_url"), str) and r["website_url"].strip()):
            results_by_id[sid] = {
                "test_status": "NOT_USEFUL", "fetch_method_found": "", "feed_url": "",
                "http_status": "", "items_recent": "", "valid_articles": "", "fulltext_ok": "",
                "date_ok": "", "problem": "NO_WEBSITE_URL", "notes": "nessun website_url in v14 (solo social/persona)",
            }

    # ID conflict override (source_id v14 coincide con un id attivo ma dominio diverso)
    for r in rows:
        if r.get("id_conflict"):
            sid = r["source_id"]
            res = results_by_id.get(sid, {})
            res["problem"] = (res.get("problem") or "") + ";ID_CONFLICT" if res.get("problem") else "ID_CONFLICT"
            res["notes"] = (res.get("notes") or "") + f" | ID_CONFLICT: source_id gia' usato da fonte attiva su dominio {active_by_id.get(sid)}"
            if res.get("test_status", "").startswith("READY"):
                res["decision_override"] = "MANUAL_REVIEW"

    # --- scrivi audit CSV per tutte le 110 righe ---
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source_id_candidate", "name", "website_url", "canonical_domain", "macro_tipo",
              "priority_tier", "technical_access", "already_active", "current_source_id",
              "test_status", "fetch_method_found", "feed_url", "http_status", "items_recent",
              "valid_articles", "fulltext_ok", "date_ok", "duplicate_rate_sample", "problem",
              "decision", "notes"]
    with open(AUDIT_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            sid = r["source_id"]
            res = results_by_id.get(sid, {
                "test_status": "MANUAL_REVIEW", "fetch_method_found": "", "feed_url": "",
                "http_status": "", "items_recent": "", "valid_articles": "", "fulltext_ok": "",
                "date_ok": "", "problem": "", "notes": "riga non classificata dallo script (controllo manuale)",
            })
            decision = res.get("decision_override", "")
            if not decision:
                if r["already_active"]:
                    decision = "ALREADY_ACTIVE"
                elif res.get("test_status", "").startswith("READY"):
                    decision = "CANDIDATE_FOR_PROMOTION"
                elif res.get("test_status") == "" and "NOT_TESTED" in res.get("notes", ""):
                    decision = "NOT_TESTED"
                else:
                    decision = "NOT_PROMOTED"
            w.writerow({
                "source_id_candidate": sid, "name": r.get("nome_fonte", ""),
                "website_url": r.get("website_url", "") or "", "canonical_domain": r["canon_domain"],
                "macro_tipo": r.get("macro_tipo", ""), "priority_tier": r.get("priority_tier", ""),
                "technical_access": r.get("technical_access", ""), "already_active": r["already_active"],
                "current_source_id": r["current_source_id"], "test_status": res.get("test_status", ""),
                "fetch_method_found": res.get("fetch_method_found", ""), "feed_url": res.get("feed_url", ""),
                "http_status": res.get("http_status", ""), "items_recent": res.get("items_recent", ""),
                "valid_articles": res.get("valid_articles", ""), "fulltext_ok": res.get("fulltext_ok", ""),
                "date_ok": res.get("date_ok", ""), "duplicate_rate_sample": "N/A_SINGLE_SOURCE",
                "problem": res.get("problem", ""), "decision": decision, "notes": res.get("notes", ""),
            })
    print(f"\nAudit CSV scritto: {AUDIT_CSV} ({len(rows)} righe, {len(tested_ids)} testate live)")

    # --- frammento YAML proposto (READY_RSS / READY_SITEMAP, non ID_CONFLICT) per revisione manuale ---
    proposals = []
    for r in rows:
        sid = r["source_id"]
        res = results_by_id.get(sid, {})
        if r["already_active"] or r.get("id_conflict"):
            continue
        if res.get("test_status") in ("READY_RSS", "READY_SITEMAP"):
            proposals.append((r, res))
    proposals.sort(key=lambda pr: rank_key(pr[0]))

    with open(SCRATCH_PROPOSED, "w", encoding="utf-8") as f:
        f.write("# proposte generate da pilot/source_audit_v14.py — SOLO READY_RSS/READY_SITEMAP,\n")
        f.write("# metodo compatibile con pilot/collect.py (rss o sitemap). Revisione manuale prima\n")
        f.write("# di appendere a config/sources.yaml. Ordinate per rank (tier, doboj, ij, elezioni, istituzionale, tech).\n")
        for r, res in proposals:
            f.write(f"- source_id: {r['source_id']}\n")
            f.write(f"  name: {json.dumps(r['nome_fonte'], ensure_ascii=False)}\n")
            f.write(f"  feed_url: {json.dumps(res['feed_url']) if res.get('feed_url') else 'null'}\n")
            f.write(f"  fetch_mode: {'rss' if res['test_status']=='READY_RSS' else 'html'}\n")
            f.write(f"  method: {'rss' if res['test_status']=='READY_RSS' else 'sitemap+html'}\n")
            f.write(f"  macro_tipo: {r.get('macro_tipo','')}\n")
            f.write(f"  ij: {r.get('ij','')}\n")
            f.write(f"  items_recent: {res.get('items_recent')}\n")
            f.write(f"  website_url: {json.dumps(r['website_url'])}\n\n")
    print(f"Frammento proposte scritto: {SCRATCH_PROPOSED} ({len(proposals)} candidati READY_RSS/READY_SITEMAP)")

    # --- problems csv ---
    PROBLEMS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pfields = ["source_id", "name", "url", "timestamp", "problem_code", "http_status", "stage", "detail", "retryable", "recommended_action"]
    retryable_codes = {"TIMEOUT", "BLOCKED_429", "RATE_LIMIT"}
    with open(PROBLEMS_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=pfields)
        w.writeheader()
        for r in rows:
            sid = r["source_id"]
            res = results_by_id.get(sid, {})
            ts = res.get("test_status", "")
            problem = res.get("problem", "")
            if not problem or r["already_active"]:
                continue
            action = {
                "BLOCKED_403": "rivedere User-Agent/IP o scartare", "BLOCKED_429": "ritentare piu' tardi con backoff",
                "TIMEOUT": "ritentare piu' tardi", "SSL_ERROR": "verificare certificato manualmente",
                "DEAD_DOMAIN": "scartare o verificare URL aggiornato", "ROBOTS_RESTRICTED": "scartare, robots.txt vieta l'accesso",
                "JS_ONLY": "scartare (no browser automation in questo task)", "NO_ARTICLE_LINKS": "MANUAL_REVIEW",
                "RSS_EMPTY": "MANUAL_REVIEW, rivedere in futuro", "ID_CONFLICT": "MANUAL_REVIEW, non rinominare automaticamente",
                "NO_WEBSITE_URL": "nessuna azione, solo social/persona",
            }.get(problem.split(";")[0], "MANUAL_REVIEW")
            w.writerow({
                "source_id": sid, "name": r.get("nome_fonte", ""), "url": r.get("website_url", "") or "",
                "timestamp": NOW.isoformat().replace("+00:00", "Z"), "problem_code": problem,
                "http_status": res.get("http_status", ""), "stage": "source_expansion_audit_01",
                "detail": res.get("notes", ""), "retryable": problem.split(";")[0] in retryable_codes,
                "recommended_action": action,
            })
    print(f"Problems CSV scritto: {PROBLEMS_CSV}")


if __name__ == "__main__":
    main()
