"""§1a, TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01: contabilita' spese LLM.

Copre SOLO il costo delle chiamate API (Anthropic/DeepSeek) fatte via pilot.llm.llm(). Il volume
di richieste di scraping per fonte (fetch, errori HTTP, item per fonte) e' un'altra cosa e vive in
data/pipeline_health.json — vedi pilot.manage per quello, non qui.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from pilot import miniyaml

ROOT = Path(__file__).resolve().parent.parent
PRICING_YAML = ROOT / "config" / "pricing.yaml"
SPEND_JSONL = ROOT / "data" / "spend.jsonl"


def load_pricing():
    return miniyaml.load(PRICING_YAML) if PRICING_YAML.exists() else {}


def cost_usd(model, in_tok, out_tok, pricing=None):
    pricing = load_pricing() if pricing is None else pricing
    rates = (pricing.get("models") or {}).get(model)
    if not rates:
        return 0.0
    return round(in_tok / 1_000_000 * rates.get("input_per_1m_usd", 0)
                 + out_tok / 1_000_000 * rates.get("output_per_1m_usd", 0), 6)


def _read_rows():
    if not SPEND_JSONL.exists():
        return []
    return [json.loads(l) for l in SPEND_JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]


def today_spend_usd(pricing=None):
    today = datetime.now(timezone.utc).date().isoformat()
    return sum(r["usd"] for r in _read_rows() if r["ts"].startswith(today))


def check_cap():
    """Chiamato da pilot.llm.llm() PRIMA della richiesta HTTP, fuori dal suo try/except: deve
    propagare un errore vero, non essere inghiottito nel degrado a None delle chiamate fallite."""
    pricing = load_pricing()
    cap = pricing.get("daily_usd_cap")
    if cap is None:
        return
    spent = today_spend_usd(pricing)
    if spent >= cap:
        raise RuntimeError(
            f"tetto di spesa giornaliero superato: ${spent:.4f} >= ${cap} (config/pricing.yaml). "
            "Nessuna chiamata API effettuata."
        )


def record(provider, model, in_tok, out_tok, caller):
    usd = cost_usd(model, in_tok, out_tok)
    row = {"ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "provider": provider,
           "model": model, "in_tok": in_tok, "out_tok": out_tok, "usd": usd, "caller": caller}
    SPEND_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(SPEND_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def report(days=None):
    rows = _read_rows()
    if days:
        min_ordinal = datetime.now(timezone.utc).date().toordinal() - days
        rows = [r for r in rows if datetime.fromisoformat(r["ts"][:10]).toordinal() >= min_ordinal]
    total = sum(r["usd"] for r in rows)
    by_model, by_day, by_caller = {}, {}, {}
    for r in rows:
        by_model[r["model"]] = round(by_model.get(r["model"], 0) + r["usd"], 6)
        by_day[r["ts"][:10]] = round(by_day.get(r["ts"][:10], 0) + r["usd"], 6)
        by_caller[r["caller"]] = round(by_caller.get(r["caller"], 0) + r["usd"], 6)
    return {"total_usd": round(total, 4), "n_calls": len(rows), "by_model": by_model,
            "by_day": by_day, "by_caller": by_caller}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", action="store_true", help="stampa il report di spesa")
    ap.add_argument("--days", type=int, default=None, help="limita agli ultimi N giorni")
    args = ap.parse_args()
    if not args.report:
        ap.error("usa --report [--days N]")
    r = report(args.days)
    print(f"totale: ${r['total_usd']} su {r['n_calls']} chiamate")
    print(f"per modello: {r['by_model']}")
    print(f"per giorno: {r['by_day']}")
    print(f"per caller: {r['by_caller']}")


if __name__ == "__main__":
    main()
