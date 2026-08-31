"""§C6 — un solo entry point per l'intera pipeline: collect -> clean -> entities -> dedup ->
score -> trending -> signals -> export_dashboard, con i conteggi di ogni stadio stampati in
catena. Si ferma al primo stadio che produce zero: sbagliare l'ordine a mano ha gia' prodotto
numeri falsi in passato (TASK_BETA_02.md §C6 - serve rilanciare 'entities' e POI 'dedup', non solo
'score', dopo ogni modifica a dashboard-config.js). `run_retry.bat`/`rerun_retry.bat` esistenti
sono il retry delle annotazioni DeepSeek del golden set, non questa pipeline: verificato, non la
coprono.

MEDIA_PILOT_FINAL_HANDOFF.md §K: scrive data/pipeline_health.json a fine corsa (last_run,
sources_ok/failed, conteggi, durata) — un fallimento di UNA fonte non blocca mai la pipeline
(gia' vero in collect.py, qui si limita a registrarlo)."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pilot import clean, collect, dedup, entities, export_dashboard, score, signals, trending

ROOT = Path(__file__).resolve().parent.parent
HEALTH_JSON = ROOT / "data" / "pipeline_health.json"
ERRORS_JSONL = ROOT / "data" / "errors.jsonl"


class PipelineStopped(Exception):
    def __init__(self, stage):
        super().__init__(stage)
        self.stage = stage


def _stop(stage):
    print(f"\nSTOP: '{stage}' ha prodotto 0 item. Pipeline interrotta qui, nessuno stadio successivo eseguito.")
    raise PipelineStopped(stage)


def _errors_since(run_start_iso):
    """§K/§1c: dettaglio errori HTTP per fonte in QUESTA esecuzione — errors.jsonl e' append-only
    su tutte le esecuzioni storiche, va filtrato per timestamp. Ritorna {source_id: {count,
    last_kind, last_message}}."""
    if not ERRORS_JSONL.exists():
        return {}
    detail = {}
    with open(ERRORS_JSONL, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("timestamp", "") < run_start_iso:
                continue
            sid = rec.get("source_id")
            d = detail.setdefault(sid, {"count": 0, "last_kind": None, "last_message": None})
            d["count"] += 1
            d["last_kind"] = rec.get("kind")
            d["last_message"] = rec.get("message")
    return detail


def run(days=collect.BACKFILL_DAYS_DEFAULT, do_collect=True, only_source_ids=None):
    t0 = time.time()
    run_start_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources_enabled = len(collect.load_sources()) if only_source_ids is None else len(only_source_ids)
    s = {"raw_items": [], "per_source": {}, "items_written": 0, "cleaned": [], "deduped": [], "clusters": [],
         "scored_items": [], "trending_rows": [], "trending_active": [], "signal_rows": [],
         "signal_review": [], "entries": []}
    ok, failed_stage, error_message = True, None, None

    try:
        if do_collect:
            print("=== collect ===")
            s["raw_items"], s["per_source"], s["items_written"] = collect.collect(days=days, only_source_ids=only_source_ids)
            if not s["raw_items"]:
                _stop("collect")
        else:
            print("=== collect === (saltato, --no-collect: riuso data/raw esistente)")

        print("\n=== clean ===")
        s["cleaned"] = clean.clean()
        if not s["cleaned"]:
            _stop("clean")

        print("\n=== entities === (rigenera config/entities.yaml da dashboard-config.js)")
        entities.main()

        print("\n=== dedup ===")
        s["deduped"], s["clusters"] = dedup.run()
        if not s["deduped"]:
            _stop("dedup")
        if not s["clusters"]:
            _stop("dedup (clustering)")

        print("\n=== score ===")
        s["scored_items"], scored_clusters = score.run()
        if not s["scored_items"]:
            _stop("score")

        print("\n=== trending ===")
        s["trending_rows"] = trending.run()
        s["trending_active"] = trending.export_trending_json(s["trending_rows"])

        print("\n=== signals ===")
        s["signal_rows"] = signals.run()
        s["signal_review"] = signals.export_signals_json(s["signal_rows"])

        print("\n=== export_dashboard ===")
        s["entries"] = export_dashboard.export_rassegna()
        if not s["entries"]:
            _stop("export_dashboard")

        print("\n=== riepilogo catena ===")
        print(f"clean: {len(s['cleaned'])} -> dedup: {len(s['deduped'])} -> cluster: {len(s['clusters'])} "
              f"-> rassegna: {len(s['entries'])} -> trending attive: {len(s['trending_active'])} "
              f"-> signal REVIEW: {len(s['signal_review'])}")
    except PipelineStopped as e:
        ok, failed_stage, error_message = False, e.stage, f"stadio '{e.stage}' ha prodotto 0 item"
    except Exception as e:
        ok, failed_stage, error_message = False, "unhandled", str(e)[:500]
        _write_health(t0, run_start_iso, sources_enabled, do_collect, s, ok, failed_stage, error_message)
        raise

    _write_health(t0, run_start_iso, sources_enabled, do_collect, s, ok, failed_stage, error_message)
    if not ok:
        sys.exit(1)


def _write_health(t0, run_start_iso, sources_enabled, do_collect, s, ok, failed_stage, error_message):
    """§1c: scritto SEMPRE a fine run, anche se un stadio si e' fermato o e' esplosa un'eccezione
    (prima solo il successo scriveva questo file — il run schedulato interrotto il 2026-08-29
    ha lasciato pipeline_health.json fermo su un run precedente, invisibile all'utente)."""
    error_detail = _errors_since(run_start_iso) if do_collect else {}
    named_failed = {sid: d for sid, d in error_detail.items() if sid}
    per_source = s["per_source"]
    health = {
        "last_run": run_start_iso,
        "run_finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ok": ok,
        "failed_stage": failed_stage,
        "error": error_message,
        "sources_enabled": sources_enabled,
        "sources_ok": max(sources_enabled - len(named_failed), 0) if do_collect else None,
        "sources_failed": sorted(named_failed) if do_collect else None,
        "sources_failed_detail": error_detail if do_collect else None,
        "sources_zero_items": sorted(sid for sid, n in per_source.items() if n == 0) if do_collect else None,
        "items_per_source": per_source if do_collect else None,
        "new_items_this_run": len(s["raw_items"]),  # item SCARICATI, non scritti - vedi items_written
        "items_fetched": len(s["raw_items"]),
        "items_written": s["items_written"],
        "clean_total": len(s["cleaned"]), "dedup_total": len(s["deduped"]), "clusters_total": len(s["clusters"]),
        "rassegna_total": len(s["entries"]), "trending_entities_registry": len(s["trending_rows"]),
        "trending_entities_active": len(s["trending_active"]),
        "signal_candidates_total": len(s["signal_rows"]), "signal_review": len(s["signal_review"]),
        "duration_sec": round(time.time() - t0, 1),
    }
    HEALTH_JSON.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_JSON.write_text(json.dumps(health, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"\nsalute pipeline scritta in {HEALTH_JSON.relative_to(ROOT)}: ok={ok} failed_stage={failed_stage}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=collect.BACKFILL_DAYS_DEFAULT,
                     help="finestra di raccolta in giorni (default: %(default)s)")
    ap.add_argument("--no-collect", action="store_true",
                     help="salta la raccolta di rete, riparte da data/raw/ gia' presente")
    args = ap.parse_args()
    run(days=args.days, do_collect=not args.no_collect)


if __name__ == "__main__":
    main()
