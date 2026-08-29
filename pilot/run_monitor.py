"""§D, MEDIA_PILOT_FINAL_HANDOFF.md — scheduler/configurazione frequenze SENZA overengineering
(§9: "non costruire un orchestratore interno complesso... Windows Task Scheduler oppure cron").
Questo script e' solo il pezzo che manca a un cron/Task Scheduler esterno: legge
config/monitoring.yaml e risolve QUALI fonti raccogliere per una priorita' o un target, cosi' un
job pianificato ogni 2h puo' raccogliere solo le fonti HIGH senza rifare anche le LOW ogni volta.
Il resto della pipeline (clean/dedup/score/trending/signals/export) gira sempre per intero — non
si puo' deduplicare/clusterizzare un sottoinsieme senza il resto del corpus come contesto.

Esempi (l'utente configura l'orario in Task Scheduler/cron, non questo script):
  python -m pilot.run_monitor --priority high
  python -m pilot.run_monitor --target doboj
  python -m pilot.run_monitor --priority high --priority medium
"""
import argparse

from pilot import miniyaml, run_all

MONITORING_YAML = run_all.collect.ROOT / "config" / "monitoring.yaml"


def load_monitoring():
    return miniyaml.load(MONITORING_YAML).get("monitoring", [])


def resolve_source_ids(targets, priorities=None, target_ids=None):
    """Unione dei source_id dei target che matchano priorita' e/o id richiesti — una fonte
    condivisa da piu' target viene raccolta una sola volta (§8)."""
    selected = set()
    matched = []
    for t in targets:
        if not t.get("enabled", True):
            continue
        if priorities and t.get("priority") not in priorities:
            continue
        if target_ids and t.get("id") not in target_ids:
            continue
        if not priorities and not target_ids:
            continue
        matched.append(t["id"])
        selected.update(t.get("source_ids") or [])
    return selected, matched


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--priority", action="append", choices=["high", "medium", "low"],
                     help="raccoglie tutti i target con questa priorita' (ripetibile)")
    ap.add_argument("--target", action="append", dest="target_ids",
                     help="raccoglie solo questo target per id (ripetibile), vedi config/monitoring.yaml")
    ap.add_argument("--days", type=int, default=None,
                     help="finestra di raccolta in giorni (default: history_days massimo fra i target selezionati)")
    args = ap.parse_args()

    if not args.priority and not args.target_ids:
        ap.error("serve almeno --priority o --target (altrimenti usa 'python -m pilot.run_all')")

    targets = load_monitoring()
    source_ids, matched = resolve_source_ids(targets, priorities=args.priority, target_ids=args.target_ids)
    if not matched:
        ap.error(f"nessun target in config/monitoring.yaml corrisponde a priority={args.priority} target={args.target_ids}")

    days = args.days
    if days is None:
        matched_cfgs = [t for t in targets if t["id"] in matched]
        days = max((t.get("history_days") or run_all.collect.BACKFILL_DAYS_DEFAULT) for t in matched_cfgs)

    print(f"target selezionati: {matched} -> {len(source_ids)} fonti distinte, finestra {days}gg")
    run_all.run(days=days, do_collect=True, only_source_ids=source_ids)


if __name__ == "__main__":
    main()
