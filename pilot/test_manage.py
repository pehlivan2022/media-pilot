"""§1b, TASK_CONTROL_PLUGIN_E_DASHBOARD_APPLIKE_01: round-trip non distruttivo su config/*.yaml.
assert puri, nessun framework di fixture — eseguibile con `pytest` o `python -m pilot.test_manage`.
Scrive davvero sui file reali (e' proprio quello che deve dimostrare), poi li ripristina byte per
byte.
"""
import sys

from pilot import manage

FAKE_SOURCE_ID = "TEST_ROUNDTRIP_999"


def test_add_source_to_target_inserts_one_line_byte_identical_otherwise():
    before = manage.MONITORING_YAML.read_text(encoding="utf-8")
    manage.add_source_to_target("background", FAKE_SOURCE_ID, dry_run=False)
    after = manage.MONITORING_YAML.read_text(encoding="utf-8")

    before_lines = before.splitlines()
    after_lines = after.splitlines()
    inserted = f"      - {FAKE_SOURCE_ID}"
    assert inserted in after_lines
    after_without_fake = [l for l in after_lines if l != inserted]
    assert after_without_fake == before_lines, "il round-trip ha toccato altre righe oltre l'inserimento"

    # rimuovi la fonte finta: ripristino byte per byte
    manage.MONITORING_YAML.write_text(before, encoding="utf-8", newline="\n")
    restored = manage.MONITORING_YAML.read_text(encoding="utf-8")
    assert restored == before, "il file non e' tornato identico all'originale dopo la rimozione"


def test_add_source_appends_entry_and_bumps_count_byte_identical_otherwise():
    before = manage.SOURCES_YAML.read_text(encoding="utf-8")
    manage.add_source(FAKE_SOURCE_ID, "Fonte finta", "https://example.com/feed", "rss", dry_run=False)
    after = manage.SOURCES_YAML.read_text(encoding="utf-8")

    before_lines = before.splitlines()
    after_lines = after.splitlines()
    assert f"  - source_id: {FAKE_SOURCE_ID}" in after_lines
    old_count = int(next(l for l in before_lines if l.startswith("count:")).split(":", 1)[1].strip())
    new_count = int(next(l for l in after_lines if l.startswith("count:")).split(":", 1)[1].strip())
    assert new_count == old_count + 1

    # tutte le righe preesistenti restano identiche e nello stesso ordine relativo, a parte il
    # blocco nuovo inserito prima della riga 'count:' e la riga 'count:' stessa aggiornata
    before_without_count = [l for l in before_lines if not l.startswith("count:")]
    after_fake_block_start = after_lines.index(f"  - source_id: {FAKE_SOURCE_ID}")
    after_without_new_block_and_count = (
        after_lines[:after_fake_block_start]
        + [l for l in after_lines[after_fake_block_start:] if not l.startswith("count:")
           and l not in _fake_source_block_lines()]
    )
    assert after_without_new_block_and_count == before_without_count

    manage.SOURCES_YAML.write_text(before, encoding="utf-8", newline="\n")
    assert manage.SOURCES_YAML.read_text(encoding="utf-8") == before


def _fake_source_block_lines():
    return [
        f"  - source_id: {FAKE_SOURCE_ID}",
        '    name: "Fonte finta"',
        '    feed_url: "https://example.com/feed"',
        "    fetch_mode: rss",
        "    method: rss",
        "    language: sr",
        "    script: latn",
        "    source_type: manual_add",
        "    owner_group: null  # non verificato, vedi napomena registry",
        '    territory: "ALL"',
        "    enabled: true",
        "    last_verified_at: null  # aggiunta via pilot.manage, mai verificata dal vivo",
        "    items_7d_at_audit: null",
        "    window_actual_days: null",
        '    website_url: "https://example.com/feed"',
    ]


def run_all():
    fns = [v for k, v in dict(globals()).items() if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"OK   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} test passati")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    run_all()
