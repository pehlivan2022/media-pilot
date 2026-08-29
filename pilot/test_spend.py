"""§1a, TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01: assert puri sul calcolo costo e sul tetto di
spesa. Eseguibile con `pytest` o `python -m pilot.test_spend`."""
import sys

from pilot import spend

_PRICING = {"models": {"fake-model": {"input_per_1m_usd": 2.0, "output_per_1m_usd": 10.0}}}


def test_cost_usd_matches_per_million_rates():
    usd = spend.cost_usd("fake-model", in_tok=1_000_000, out_tok=500_000, pricing=_PRICING)
    assert usd == 2.0 + 5.0


def test_cost_usd_unknown_model_is_zero_not_a_crash():
    assert spend.cost_usd("modello-mai-sentito", 1000, 1000, pricing=_PRICING) == 0.0


def test_check_cap_raises_when_today_spend_meets_cap(monkeypatch):
    monkeypatch.setattr(spend, "load_pricing", lambda: {"daily_usd_cap": 1.0})
    monkeypatch.setattr(spend, "today_spend_usd", lambda pricing=None: 1.5)
    raised = False
    try:
        spend.check_cap()
    except RuntimeError:
        raised = True
    assert raised, "check_cap() deve sollevare RuntimeError quando la spesa di oggi >= al tetto"


def test_check_cap_noop_when_no_cap_configured(monkeypatch):
    monkeypatch.setattr(spend, "load_pricing", lambda: {"daily_usd_cap": None})
    spend.check_cap()  # non deve sollevare nulla


def run_all():
    ns = dict(globals())
    fns = [v for k, v in ns.items() if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            if "monkeypatch" in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
                class _MP:
                    def setattr(self, obj, name, value):
                        setattr(obj, name, value)
                fn(_MP())
            else:
                fn()
            print(f"OK   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} test passati")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_all()
