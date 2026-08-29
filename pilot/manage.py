"""§1b, TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01: aggiunge fonti/keyword a config/*.yaml
preservando commenti e formattazione — edit di testo mirato, MAI load -> dump (regola 0.2 del
task: config/ e' scritto a mano e i commenti valgono).

Sottocomandi:
  add-source --id ID --name NOME --url URL --type {rss,html} [--target TARGET] [--dry-run]
  add-keyword --term PAROLA [--topic TOPIC] [--dry-run]
      NOTA: config/topics.yaml oggi e' una singola lista piatta 'weak_keywords', non raggruppata
      per topic (verificato leggendo il file) — --topic e' accettato per compatibilita' col
      prompt ma non ha effetto: ogni termine finisce in weak_keywords. Se serve raggruppamento
      per topic va deciso come task separato, non improvvisato qui.
  list-sources [--enabled] [--target TARGET]
  check-sources
  status
"""
import argparse
import difflib
import sys
from datetime import datetime, timezone
from pathlib import Path

from pilot import miniyaml, spend

if hasattr(sys.stdout, "reconfigure"):
    # nomi fonte con cirillico/diacritici (es. 'đ') altrimenti crashano su console cp1252 di
    # Windows quando lo script gira senza PYTHONIOENCODING=utf-8 (visto dal vivo con list-sources).
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SOURCES_YAML = ROOT / "config" / "sources.yaml"
TOPICS_YAML = ROOT / "config" / "topics.yaml"
MONITORING_YAML = ROOT / "config" / "monitoring.yaml"
HEALTH_JSON = ROOT / "data" / "pipeline_health.json"


def _yaml_str(s):
    return '"' + s.replace('"', '\\"') + '"'


def _diff_and_write(path, old_text, new_text, dry_run):
    if old_text == new_text:
        print("(nessuna modifica)")
        return
    diff = "".join(difflib.unified_diff(
        old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
        fromfile=str(path.name), tofile=str(path.name)))
    print(diff)
    if dry_run:
        print(f"--dry-run: {path} non modificato")
    else:
        path.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"scritto: {path}")


# ---------------------------------------------------------------------------
# add-source
# ---------------------------------------------------------------------------

def add_source(source_id, name, url, source_type, target=None, dry_run=False):
    existing_ids = {s["source_id"] for s in miniyaml.load(SOURCES_YAML).get("sources", [])}
    if source_id in existing_ids:
        raise SystemExit(f"errore: source_id gia' esistente in sources.yaml: {source_id}")

    text = SOURCES_YAML.read_text(encoding="utf-8")
    feed_url = _yaml_str(url) if source_type == "rss" else "null"
    entry = (
        f"  - source_id: {source_id}\n"
        f"    name: {_yaml_str(name)}\n"
        f"    feed_url: {feed_url}\n"
        f"    fetch_mode: {source_type}\n"
        f"    method: {source_type}\n"
        f"    language: sr\n"
        f"    script: latn\n"
        f"    source_type: manual_add\n"
        f"    owner_group: null  # non verificato, vedi napomena registry\n"
        f'    territory: "ALL"\n'
        f"    enabled: true\n"
        f"    last_verified_at: null  # aggiunta via pilot.manage, mai verificata dal vivo\n"
        f"    items_7d_at_audit: null\n"
        f"    window_actual_days: null\n"
        f"    website_url: {_yaml_str(url)}\n"
    )
    lines = text.splitlines(keepends=True)
    count_idx = next((i for i, l in enumerate(lines) if l.strip().startswith("count:")), None)
    if count_idx is None:
        raise SystemExit("errore: riga 'count: N' non trovata in sources.yaml, formato inatteso")
    old_count = int(lines[count_idx].strip().split(":", 1)[1].strip())
    new_lines = lines[:count_idx] + [entry] + [f"count: {old_count + 1}\n"]
    _diff_and_write(SOURCES_YAML, text, "".join(new_lines), dry_run)

    if target:
        add_source_to_target(target, source_id, dry_run=dry_run)


def add_source_to_target(target_id, source_id, dry_run=False):
    targets = {t["id"] for t in miniyaml.load(MONITORING_YAML).get("monitoring", [])}
    if target_id not in targets:
        raise SystemExit(f"errore: target '{target_id}' non esiste in monitoring.yaml")

    text = MONITORING_YAML.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    start = next(i for i, l in enumerate(lines) if l.strip() == f"- id: {target_id}")
    end = len(lines)
    for i in range(start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("- id:") or (lines[i][:2] != "  " and stripped):
            end = i
            break
    block = lines[start:end]

    src_idx = next((i for i, l in enumerate(block) if l.strip() == "source_ids:"), None)
    if src_idx is None:
        raise SystemExit(f"errore: target '{target_id}' non ha una chiave source_ids:")
    if any(l.strip() == f"- {source_id}" for l in block[src_idx + 1:]):
        print(f"'{source_id}' e' gia' in source_ids di '{target_id}', nessuna modifica")
        return
    insert_at = src_idx + 1
    while insert_at < len(block) and block[insert_at].strip().startswith("- "):
        insert_at += 1
    block = block[:insert_at] + [f"      - {source_id}\n"] + block[insert_at:]

    new_lines = lines[:start] + block + lines[end:]
    _diff_and_write(MONITORING_YAML, text, "".join(new_lines), dry_run)


# ---------------------------------------------------------------------------
# add-keyword
# ---------------------------------------------------------------------------

def add_keyword(term, topic=None, dry_run=False):
    if topic:
        print("nota: topics.yaml non ha raggruppamento per topic (solo weak_keywords piatta) - "
              "--topic ignorato, il termine va comunque in weak_keywords")
    existing = set(miniyaml.load(TOPICS_YAML).get("weak_keywords", []))
    if term in existing:
        print(f"'{term}' e' gia' in weak_keywords, nessuna modifica")
        return
    text = TOPICS_YAML.read_text(encoding="utf-8")
    new_text = text if text.endswith("\n") else text + "\n"
    new_text += f"  - {term}\n"
    _diff_and_write(TOPICS_YAML, text, new_text, dry_run)


# ---------------------------------------------------------------------------
# list-sources / check-sources
# ---------------------------------------------------------------------------

def list_sources(enabled_only=False, target=None):
    sources = miniyaml.load(SOURCES_YAML).get("sources", [])
    if enabled_only:
        sources = [s for s in sources if s.get("enabled")]
    if target:
        targets = miniyaml.load(MONITORING_YAML).get("monitoring", [])
        t = next((t for t in targets if t["id"] == target), None)
        if t is None:
            raise SystemExit(f"errore: target '{target}' non esiste in monitoring.yaml")
        ids = set(t.get("source_ids") or [])
        sources = [s for s in sources if s["source_id"] in ids]
    for s in sources:
        print(f"{s['source_id']:16} enabled={s.get('enabled')!s:5} {s.get('name')}")
    print(f"\n{len(sources)} fonti")


def check_sources():
    sources = {s["source_id"] for s in miniyaml.load(SOURCES_YAML).get("sources", [])}
    targets = miniyaml.load(MONITORING_YAML).get("monitoring", [])
    used = set()
    referenced_missing = set()
    for t in targets:
        for sid in (t.get("source_ids") or []):
            used.add(sid)
            if sid not in sources:
                referenced_missing.add(sid)
    unused = sources - used
    print(f"fonti in monitoring.yaml ma NON in sources.yaml ({len(referenced_missing)}): "
          f"{sorted(referenced_missing)}")
    print(f"fonti in sources.yaml MAI usate da un target ({len(unused)}): {sorted(unused)}")


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

def status():
    if not HEALTH_JSON.exists():
        print("data/pipeline_health.json non esiste ancora — nessun run registrato")
    else:
        import json
        h = json.loads(HEALTH_JSON.read_text(encoding="utf-8"))
        print(f"ultimo run: {h.get('last_run')}  ok={h.get('ok', True)}  "
              f"durata={h.get('duration_sec')}s")
        print(f"fonti: {h.get('sources_ok')} ok / {h.get('sources_enabled')} abilitate")
        failed = h.get("sources_failed") or []
        if failed:
            print(f"fonti fallite ({len(failed)}): {failed}")
        zero = h.get("sources_zero_items")
        if zero:
            print(f"fonti a zero item in questo run ({len(zero)}): {zero}")
    spesa = spend.today_spend_usd()
    print(f"spesa LLM di oggi: ${spesa:.4f}")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add-source")
    p.add_argument("--id", required=True, dest="source_id")
    p.add_argument("--name", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--type", required=True, choices=["rss", "html"], dest="source_type")
    p.add_argument("--target", default=None)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("add-keyword")
    p.add_argument("--term", required=True)
    p.add_argument("--topic", default=None)
    p.add_argument("--dry-run", action="store_true")

    p = sub.add_parser("list-sources")
    p.add_argument("--enabled", action="store_true")
    p.add_argument("--target", default=None)

    sub.add_parser("check-sources")
    sub.add_parser("status")

    args = ap.parse_args()
    if args.cmd == "add-source":
        add_source(args.source_id, args.name, args.url, args.source_type, args.target, args.dry_run)
    elif args.cmd == "add-keyword":
        add_keyword(args.term, args.topic, args.dry_run)
    elif args.cmd == "list-sources":
        list_sources(args.enabled, args.target)
    elif args.cmd == "check-sources":
        check_sources()
    elif args.cmd == "status":
        status()


if __name__ == "__main__":
    main()
