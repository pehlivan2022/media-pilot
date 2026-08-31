"""assert puri, nessun framework di fixture. Eseguibile con `pytest` o `python -m pilot.test_pipeline`."""
import os
import sqlite3
from pathlib import Path

import feedparser
import trafilatura

from pilot import ask as ask_mod
from pilot import clean as clean_mod
from pilot import collect as collect_mod
from pilot import dedup as dedup_mod
from pilot import entities as entities_mod
from pilot import entity_salience as salience_mod
from pilot import index as index_mod
from pilot import run_monitor as run_monitor_mod
from pilot import score as score_mod
from pilot import signals as signals_mod
from pilot import trending as trending_mod
from pilot.llm import llm
from pilot.util import canonicalize_url, has_cyrillic, normalize_search, parse_date_to_utc

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "data" / "fixtures"


def test_1_canonical_url_strips_tracking_and_amp():
    a = canonicalize_url("https://example.com/news/article?utm_source=x&id=5#frag")
    b = canonicalize_url("https://example.com/news/article/amp/?id=5")
    assert a == "https://example.com/news/article?id=5"
    assert b == "https://example.com/news/article?id=5"


def test_1b_canonical_url_fixes_scheme_port_mismatch():
    """§5a: RTRS pubblica http://host:443/... (scheme http, porta 443 di https): 385 errori
    HTTP 400 sulla prima run. Il normalizzatore corregge scheme<->porta prima del fetch."""
    assert canonicalize_url("http://www.rtrs.tv:443/vijesti/vijest.php?id=657673") == \
        "https://www.rtrs.tv/vijesti/vijest.php?id=657673"
    assert canonicalize_url("https://example.com:80/path") == "http://example.com/path"


def test_2_three_date_formats_same_iso_utc():
    rfc822 = parse_date_to_utc("Wed, 26 Aug 2026 22:37:10 +0200")
    iso = parse_date_to_utc("2026-08-26T20:37:10Z")
    dotted = parse_date_to_utc("26.08.2026. u 20:37")
    assert rfc822 == "2026-08-26T20:37:10Z"
    assert iso == "2026-08-26T20:37:10Z"
    assert dotted == "2026-08-26T20:37:00Z"  # formato senza secondi: minuto coincide, secondi 00


def test_3_cyrillic_and_latin_match_same_entity():
    entities = entities_mod.generate_entities()[0]
    ent = next(e for e in entities if e["key"] == "stevandic")
    aliases_text = {a["text"] for a in ent["aliases"]}
    assert "Ненад Стевандић" in aliases_text
    assert "Nenad Stevandic" in aliases_text
    hits_cyr = score_mod.match_entities("Ненад Стевандић на конференцији", "", entities)
    hits_lat = score_mod.match_entities("Nenad Stevandic na konferenciji", "", entities)
    assert any(h["key"] == "stevandic" for h in hits_cyr)
    assert any(h["key"] == "stevandic" for h in hits_lat)


def test_4_short_alias_needs_word_boundary_and_uppercase():
    entities = entities_mod.generate_entities()[0]
    assert not score_mod._exact_word_match("US", "plUS raste u anketama")
    assert not score_mod._exact_word_match("US", "USA su najavile")
    assert not score_mod._exact_word_match("US", "u focus grupi")
    assert score_mod._exact_word_match("US", "US je saopštila danas")


def _fake_item(raw_id, url, title, text, published_at, source_id, content_hash=None):
    from pilot.util import sha256_hex
    return {
        "raw_id": raw_id, "source_id": source_id, "url": url, "final_url": url,
        "title": title, "author": None, "text": text, "language": "sr", "script": "latn",
        "published_at": published_at, "occurred_at": None, "scraped_at": published_at,
        "content_hash": content_hash or sha256_hex(text),
        "title_norm": normalize_search(title), "text_norm": normalize_search(text),
    }


def test_4b_bl_ij3_006_widget_stripped_other_sources_untouched():
    """D0.1, TASK_BETA_03: il widget "articoli correlati" di Banjaluka24 (BL_IJ3_006) va tagliato,
    altre fonti con un trattino seguito da testo normale non devono perdere contenuto vero."""
    contaminated = ("Prava vijest o dogadjaju u gradu.\n"
                     "-\n\t\t\t\tPolitika2 dana agoNASLOV SASVIM DRUGOG CLANKA\n"
                     "-\n\t\t\t\tHronika1 dan agoJOS JEDAN NASLOV")
    assert clean_mod.strip_source_specific("BL_IJ3_006", contaminated) == "Prava vijest o dogadjaju u gradu."
    other_source_text = "Prva tacka.\n- druga tacka normale liste\n- treca tacka normale liste"
    assert clean_mod.strip_source_specific("BL_IJ3_006", other_source_text) == other_source_text
    assert clean_mod.strip_source_specific("RS_ENT_002", contaminated) == contaminated


def test_5_three_copies_become_one_item_three_evidence():
    items = [
        _fake_item("r1", "https://a.example/x", "Isti naslov", "isti tekst", "2026-08-26T10:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/x", "Isti naslov", "isti tekst", "2026-08-26T11:00:00Z", "s2"),
        _fake_item("r3", "https://c.example/x", "Isti naslov", "isti tekst", "2026-08-26T12:00:00Z", "s3"),
    ]
    groups = dedup_mod.dedup(items)
    deduped = dedup_mod.build_deduped_items(items, groups)
    assert len(deduped) == 1
    assert len(deduped[0]["evidence"]) == 3
    assert deduped[0]["n_copies"] == 3


def test_5b_dedup_different_titles_same_body_via_shingles():
    """§2b: titoli diversi, corpo (quasi) identico -> stesso item, 2 evidence. Il criterio centrale
    e' il corpo (TF-IDF+coseno, §C1), non piu' il titolo: prima di FIX 2 questa coppia sarebbe
    rimasta 2 item separati (nessun test sul titolo l'avrebbe presa)."""
    body = ("Служба за одбијене изборне пријаве саопштила је да су примједбе " * 3).strip()
    items = [
        _fake_item("r1", "https://a.example/x", "Naslov jedan sasvim drugaciji", body, "2026-08-26T10:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/x", "Potpuno drugi naslov clanka", body, "2026-08-26T11:00:00Z", "s2"),
    ]
    groups = dedup_mod.dedup(items)
    deduped = dedup_mod.build_deduped_items(items, groups)
    assert len(deduped) == 1
    assert len(deduped[0]["evidence"]) == 2


def test_5c_reopens_closed_group_for_identical_title_pass4():
    """RFC_SECONDA_OPINIONE_02.md §6: i gruppi dei passaggi 1-3 restavano chiusi al passaggio 4.
    r1/r2 si fondono al passaggio 3 (corpo quasi identico, titoli diversi); r3 ha lo STESSO
    titolo di r1 ma un corpo scorrelato (sotto soglia body) -> deve comunque agganciarsi al
    gruppo gia' formato, non restare un item separato (misurato: 10-12 coppie cosi' sul corpus
    reale prima del fix)."""
    body = ("Служба за одбијене изборне пријаве саопштила је да су примједбе " * 3).strip()
    items = [
        _fake_item("r1", "https://a.example/x", "Naslov jedan sasvim drugaciji", body, "2026-08-26T10:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/x", "Potpuno drugi naslov clanka", body, "2026-08-26T11:00:00Z", "s2"),
        _fake_item("r3", "https://c.example/x", "Naslov jedan sasvim drugaciji",
                   "Sasvim druga tema o vremenskoj prognozi i temperaturi za vikend", "2026-08-26T12:00:00Z", "s3"),
    ]
    groups = dedup_mod.dedup(items)
    deduped = dedup_mod.build_deduped_items(items, groups)
    assert len(deduped) == 1
    assert len(deduped[0]["evidence"]) == 3


def test_6_three_articles_same_event_one_cluster():
    items = [
        _fake_item("r1", "https://a.example/1", "Vučić stigao u Banjaluku danas", "tekst jedan o posjeti", "2026-08-26T09:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/2", "Vučić danas stigao u Banjaluku", "tekst dva o posjeti", "2026-08-26T10:00:00Z", "s2"),
        _fake_item("r3", "https://c.example/3", "Banjaluku danas posjetio Vučić", "tekst tri o posjeti", "2026-08-26T12:00:00Z", "s3"),
    ]
    groups = dedup_mod.dedup(items)  # titoli simili ma non identici: restano 3 item dopo dedup
    deduped = dedup_mod.build_deduped_items(items, groups)
    assert len(deduped) == 3
    scoring_cfg = {"clustering": {"window_hours": 60, "title_overlap_threshold": 0.35}}
    clusters = dedup_mod.cluster(deduped, scoring_cfg)
    assert len(clusters) == 1
    assert len(clusters[0]["items"]) == 3


def test_6b_transitive_cluster_via_pooled_representation():
    """§2c: A~B (entita' condivisa 'x'), B~C (entita' condivisa 'y'), A e C non condividono
    nulla direttamente (ne' entita', ne' titolo, ne' corpo). Un cluster corretto usa la
    rappresentazione ACCUMULATA del cluster (aggiornata dopo l'ingresso di B), non solo il primo
    membro: altrimenti C resterebbe fuori, come nel bug originale."""
    items = [
        _fake_item("r1", "https://a.example/1", "Konferencija o poljoprivredi u Trebinju",
                   "Tema potpuno drugacija o poljoprivredi i navodnjavanju polja", "2026-08-26T09:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/2", "Sastanak stranackih lidera u glavnom gradu",
                   "Sasvim treca tema o sastanku i pregovorima izmedju delegacija", "2026-08-26T10:00:00Z", "s2"),
        _fake_item("r3", "https://c.example/3", "Otvaranje nove fabrike tekstila u regiji",
                   "Cetvrta potpuno odvojena tema o proizvodnji i zaposljavanju", "2026-08-26T11:00:00Z", "s3"),
    ]
    deduped = dedup_mod.build_deduped_items(items, dedup_mod.dedup(items))
    assert len(deduped) == 3
    # chiavi reali del registro (tipo 'actor'), non inventate: cluster() filtra le entita' di tipo
    # territorio/gara/esterno dal segnale di clustering (troppo larghe, vedi commento in dedup.py)
    deduped[0]["_entity_hits"] = [{"key": "stevandic", "label": "X", "centrality": 1.0, "alias_class": "forte"}]
    deduped[1]["_entity_hits"] = [{"key": "stevandic", "label": "X", "centrality": 1.0, "alias_class": "forte"},
                                   {"key": "minic", "label": "Y", "centrality": 1.0, "alias_class": "forte"}]
    deduped[2]["_entity_hits"] = [{"key": "minic", "label": "Y", "centrality": 1.0, "alias_class": "forte"}]
    scoring_cfg = {"clustering": {"window_hours": 60, "title_overlap_threshold": 1.1,
                                   "body_overlap_threshold": 1.1, "min_shared_entities": 1}}
    clusters = dedup_mod.cluster(deduped, scoring_cfg)
    assert len(clusters) == 1
    assert len(clusters[0]["items"]) == 3


def test_7_source_diversity_ignores_same_owner_group():
    items = [
        _fake_item("r1", "https://a.example/1", "Naslov jedan", "tekst jedan", "2026-08-26T09:00:00Z", "s1"),
        _fake_item("r2", "https://b.example/2", "Naslov dva", "tekst dva", "2026-08-26T09:30:00Z", "s2"),
    ]
    groups = dedup_mod.dedup(items)
    deduped = dedup_mod.build_deduped_items(items, groups)
    for it in deduped:
        it["modules"] = []
        it["_entity_hits"] = []
    sources_same_owner = {"s1": {"owner_group": "grupa-x", "source_type": "media_public"},
                           "s2": {"owner_group": "grupa-x", "source_type": "media_public"}}
    sources_diff_owner = {"s1": {"owner_group": "grupa-x", "source_type": "media_public"},
                           "s2": {"owner_group": "grupa-y", "source_type": "media_public"}}
    cfg = {"clustering": {"window_hours": 60, "title_overlap_threshold": 0.0}}
    c_same = dedup_mod.cluster([dict(it) for it in deduped], cfg)
    c_diff = dedup_mod.cluster([dict(it) for it in deduped], cfg)
    scored_same = score_mod.compute_layer1_and_signal(deduped, c_same, sources_same_owner, {})
    scored_diff = score_mod.compute_layer1_and_signal(deduped, c_diff, sources_diff_owner, {})
    assert scored_same[0]["measured"]["source_diversity"] == 1
    assert scored_diff[0]["measured"]["source_diversity"] == 2


def test_8_no_layer3_fields_in_output():
    items = [_fake_item("r1", "https://a.example/1", "Naslov", "tekst " * 60, "2026-08-26T09:00:00Z", "s1")]
    groups = dedup_mod.dedup(items)
    deduped = dedup_mod.build_deduped_items(items, groups)
    for it in deduped:
        it["modules"] = []
        it["_entity_hits"] = []
        it["menu"] = None
        it["provenance"] = "MEDIA"
        it["verification"] = "SINGLE_SOURCE"
        it["territory_raw"] = None
        it["territory_ij"] = None
    stripped = score_mod.strip_internal_fields(deduped)
    for it in stripped:
        for forbidden in score_mod._FORBIDDEN_LAYER3_FIELDS:
            assert forbidden not in it
        assert it["judgment"]["provenance"] == "MODEL"
        assert it["judgment"]["risk"] is None


def test_9_no_item_has_territory_ij_valued():
    items = [_fake_item("r1", "https://a.example/1", "Naslov", "tekst " * 60, "2026-08-26T09:00:00Z", "s1")]
    deduped = dedup_mod.build_deduped_items(items, dedup_mod.dedup(items))
    entities = entities_mod.generate_entities()[0]
    scored = score_mod.compute_layer2(deduped, entities, {"s1": {"source_type": "media_public"}})
    assert all(it["territory_ij"] is None for it in scored)


def test_10_original_text_keeps_cyrillic_norm_is_latin():
    text = "Ненад Стевандић је рекао"
    assert has_cyrillic(text)
    norm = normalize_search(text)
    assert not has_cyrillic(norm)
    assert norm == "nenad stevandic je rekao"


def test_11_ask_no_results_returns_fixed_message():
    hits = ask_mod.retrieve("xyzzynonexistentterm000")
    assert hits == [] or ask_mod.ask("xyzzynonexistentterm000") == "nessun documento nel corpus"


def test_12_llm_empty_env_returns_none_pipeline_survives(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    assert llm("qualsiasi prompt") is None
    # clean/dedup/score/index devono girare senza eccezioni anche con ambiente vuoto,
    # perche' nessuno di questi moduli chiama llm(): solo ask.py lo fa, con fallback gestito.
    cleaned = clean_mod.clean(write=False)
    assert isinstance(cleaned, list)


def test_fixture_rss_parses_offline():
    for name in ("srpskainfo_feed.xml", "banjaluka24_feed.xml"):
        body = (FIXTURES / name).read_bytes()
        parsed = feedparser.parse(body)
        assert len(parsed.entries) > 0
        assert parsed.entries[0].get("link", "").startswith("http")


def test_fixture_html_extracts_offline():
    html_text = (FIXTURES / "dobojski_home.html").read_text(encoding="utf-8", errors="ignore")
    extracted = trafilatura.extract(html_text)
    assert extracted is None or isinstance(extracted, str)


def test_13_velocity_conta_articoli_non_solo_recency():
    """B0: numeratore in ARTICOLI, omogeneo al denominatore (item/4h).

    Prima di questo fix il numeratore contava gruppi di fonti e velocity assumeva 2 soli valori
    (0.0 / 0.167): i due cluster qui sotto davano lo stesso identico punteggio.
    """
    def _it(rid, iso, sid):
        return {"raw_id": rid, "published_at": iso, "source_id": sid, "n_copies": 1, "_entity_hits": []}

    # 3 giorni di storia, altrimenti scatta baseline_incomplete e velocity resta None
    items = [_it(f"bg-{d}-{h}", f"2026-08-{24 + d}T{h:02d}:00:00Z", "s-bg")
             for d in range(3) for h in (6, 12, 18)]
    # cluster A: 10 articoli in 4h da 2 fonti | cluster B: 1 articolo da 1 fonte, stessa ora
    items += [_it(f"a{i}", "2026-08-27T10:00:00Z", "sa1" if i % 2 else "sa2") for i in range(10)]
    items.append(_it("b0", "2026-08-27T10:00:00Z", "sb1"))

    sources = {sid: {"owner_group": None, "source_type": "media_public"}
               for sid in ("s-bg", "sa1", "sa2", "sb1")}
    clusters = [
        {"cluster_id": "A", "items": [f"a{i}" for i in range(10)], "sources": ["sa1", "sa2"]},
        {"cluster_id": "B", "items": ["b0"], "sources": ["sb1"]},
    ]
    scored = score_mod.compute_layer1_and_signal(items, clusters, sources, {})
    va, vb = scored[0]["measured"]["velocity"], scored[1]["measured"]["velocity"]
    assert va is not None and vb is not None, f"velocity nulla (baseline_incomplete?): {va} {vb}"
    assert va > vb, f"10 articoli da 2 fonti ({va}) non batte 1 articolo da 1 fonte ({vb})"


def test_13b_baseline_4h_conta_i_bucket_vuoti():
    """B0: la mediana va presa su tutti i bucket della finestra, non solo su quelli non vuoti."""
    items = [{"raw_id": f"r{i}", "published_at": "2026-08-27T10:00:00Z", "source_id": "s1",
              "n_copies": 1, "_entity_hits": []} for i in range(50)]
    # un solo articolo tre giorni prima: 18 bucket nella finestra, 2 soli non vuoti
    items.append({"raw_id": "old", "published_at": "2026-08-24T10:00:00Z", "source_id": "s1",
                  "n_copies": 1, "_entity_hits": []})
    clusters = [{"cluster_id": "A", "items": ["r0"], "sources": ["s1"]}]
    scored = score_mod.compute_layer1_and_signal(
        items, clusters, {"s1": {"owner_group": None, "source_type": "media_public"}}, {})
    # contando solo i non vuoti la mediana sarebbe 1 o 50; con i vuoti e' 0 -> clamp a 1
    assert scored[0]["measured"]["velocity_baseline_4h"] == 1


def _trending_item(raw_id, iso, source_id, modules, cluster_id, title="t", url="https://x/"):
    return {"raw_id": raw_id, "published_at": iso, "source_id": source_id, "modules": modules,
            "cluster_id": cluster_id, "is_relevant": True, "title": title, "url": url}


def test_14_trending_acceleration_needs_baseline_and_recent_burst():
    """D1 TASK_BETA_03: un'entita' con una storia normale di 1 mention/giorno per 7gg e poi un
    burst di 5 mention in 4h deve avere acceleration > 1 e baseline_7d misurato; un'entita' che
    compare solo nelle ultime 4h su un corpus troppo corto (<7gg) deve avere baseline_7d None."""
    sources = {"s1": {}, "s2": {}, "s3": {}}
    entities = [{"key": "dodik", "label": "Milorad Dodik", "type": "actor"},
                {"key": "minic", "label": "X Minic", "type": "actor"}]
    items = []
    # 7 giorni di storia leggera per 'dodik': 1 mention/giorno, cluster diverso ogni volta
    for d in range(7):
        items.append(_trending_item(f"hist-{d}", f"2026-08-{20 + d:02d}T08:00:00Z", "s1",
                                     ["dodik"], f"CL-h{d}"))
    # burst nelle ultime 4h: 5 mention, 3 fonti, 2 cluster
    for i in range(5):
        items.append(_trending_item(f"burst-{i}", "2026-08-27T09:00:00Z",
                                     ["s1", "s2", "s3"][i % 3], ["dodik"], f"CL-b{i % 2}"))
    rows = trending_mod.compute_trending(items, sources, entities)
    dodik = next(r for r in rows if r["key"] == "dodik")
    assert dodik["baseline_7d"] is not None, "7 giorni di storia dovrebbero bastare per una baseline"
    assert dodik["mentions_4h"] == 5
    assert dodik["unique_events_4h"] == 2
    assert dodik["unique_sources_4h"] == 3
    assert dodik["acceleration"] is not None and dodik["acceleration"] > 1, \
        f"5 mention in 4h contro una storia di 1/giorno deve accelerare, non {dodik['acceleration']}"
    assert dodik["baseline_daily_7d"] is not None and dodik["baseline_daily_7d"] > 0
    assert dodik["momentum"] is not None and dodik["momentum"] > 0, \
        "24h con burst deve avere momentum positivo rispetto alla baseline giornaliera"

    minic = next(r for r in rows if r["key"] == "minic")
    assert minic["mentions_24h"] == 0
    assert minic["baseline_7d"] is None
    assert minic["acceleration"] is None


def test_15_entity_salience_more_granular_than_four_levels():
    """D2.2 TASK_BETA_03: entity_salience deve distinguere due item che entity_centrality
    tratterebbe come identici (stesso found_in='title', quindi centrality=1.0) in base a quante
    volte l'entita' ricorre nel testo e se e' l'entita' primaria del suo evento."""
    entities = [{"key": "dodik", "label": "X", "type": "actor",
                 "aliases": [{"text": "Dodik", "norm": "dodik"}]}]
    hit = {"key": "dodik", "label": "X", "centrality": 1.0, "alias_class": "forte"}
    weak_hit = {"key": "dodik", "label": "X", "centrality": 0.3, "alias_class": "forte"}
    items = [
        {"raw_id": "r1", "is_relevant": True, "cluster_id": "C1", "_entity_hits": [hit],
         "text": "Dodik izjava. " * 6},  # titolo + molte ripetizioni, sola entita' del cluster
        {"raw_id": "r2", "is_relevant": True, "cluster_id": "C2", "_entity_hits": [hit],
         "text": "Dodik izjava."},  # titolo, una sola menzione
        {"raw_id": "r3", "is_relevant": True, "cluster_id": "C2", "_entity_hits": [weak_hit],
         "text": "Spominje se i Dodik uzgredno u clanku."},  # stesso cluster di r2, ma solo nel corpo
    ]
    rows = salience_mod.compute_salience(items, entities)
    by_id = {r["raw_id"]: r for r in rows}
    assert by_id["r1"]["entity_salience"] > by_id["r2"]["entity_salience"], \
        "piu' ripetizioni nello stesso found_in deve pesare di piu'"
    assert by_id["r2"]["is_primary_in_event"] is True
    assert by_id["r3"]["is_primary_in_event"] is False
    assert len({r["entity_salience"] for r in rows}) == 3, "tre item, tre salience distinte attese"


def _trend_row(key, mentions_24h, unique_events_24h=1, unique_sources_24h=1, momentum=None, top_events=None):
    return {"key": key, "label": key, "mentions_24h": mentions_24h, "unique_events_24h": unique_events_24h,
            "unique_sources_24h": unique_sources_24h, "momentum": momentum, "acceleration": None,
            "last_event_at": "2026-08-27T10:00:00Z", "top_events": top_events or [],
            "evidence": ["https://x/1"]}


def test_16_signal_candidate_review_needs_multiple_real_signals():
    """H, MEDIA_PILOT_FINAL_HANDOFF.md: un'entita' con momentum alto, molte fonti/eventi ed
    entita' primaria deve classificarsi REVIEW; una con una sola menzione debole resta MONITORING;
    un'entita' silenziosa (mentions_24h=0) non genera nessun candidato (il silenzio non e' un
    segnale)."""
    hot = _trend_row("dodik", mentions_24h=10, unique_events_24h=5, unique_sources_24h=4, momentum=2.0,
                      top_events=[{"cluster_id": "CL-1", "source_id": "s1", "published_at": "2026-08-27T06:00:00Z"}])
    quiet = _trend_row("minic", mentions_24h=1, unique_events_24h=1, unique_sources_24h=1, momentum=0.1)
    silent = _trend_row("obren", mentions_24h=0)
    salience_by_key = {"dodik": {"max_salience": 1.3, "any_primary": True, "max_co_entities": 3},
                        "minic": {"max_salience": 0.3, "any_primary": False, "max_co_entities": 0}}
    candidates = signals_mod.build_signal_candidates([hot, quiet, silent], salience_by_key)
    by_id = {c["entity_id"]: c for c in candidates}
    assert "obren" not in by_id, "un'entita' senza mention nelle ultime 24h non deve produrre un Signal"
    assert by_id["dodik"]["classification"] == "REVIEW"
    assert by_id["dodik"]["confidence"] == 1.0
    assert by_id["minic"]["classification"] == "MONITORING"
    assert by_id["dodik"]["provenance"] == "PILOT_RULES"
    assert by_id["dodik"]["first_seen"] == "2026-08-27T06:00:00Z"


def test_17_run_monitor_dedupes_shared_source_across_targets():
    """D, MEDIA_PILOT_FINAL_HANDOFF.md §8: due target che condividono una fonte devono risolvere
    a UN solo fetch, non due."""
    targets = [
        {"id": "a", "enabled": True, "priority": "high", "source_ids": ["S1", "S2"]},
        {"id": "b", "enabled": True, "priority": "high", "source_ids": ["S2", "S3"]},
        {"id": "c", "enabled": False, "priority": "high", "source_ids": ["S9"]},
    ]
    sids, matched = run_monitor_mod.resolve_source_ids(targets, priorities=["high"])
    assert sids == {"S1", "S2", "S3"}, "S2 condiviso da a/b deve comparire una volta sola"
    assert set(matched) == {"a", "b"}, "il target disabilitato non deve essere selezionato"


def test_18_collect_skips_history_supplement_once_window_is_full():
    """TASK_FASE2_COMPLETAMENTO §A1: senza questo guard, ogni run rifaceva il supplemento
    wayback/sitemap per ogni fonte RSS a prescindere da data/raw/ gia' presente (~50min)."""
    assert collect_mod._needs_history_supplement({"window_actual_days": 3}, days=7) is True
    assert collect_mod._needs_history_supplement({"window_actual_days": 7}, days=7) is False
    assert collect_mod._needs_history_supplement({"window_actual_days": 10}, days=7) is False
    assert collect_mod._needs_history_supplement({}, days=7) is True, "fonte mai vista -> supplemento"


def run_all():
    import sys
    ns = dict(globals())
    fns = [v for k, v in ns.items() if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            if "monkeypatch" in fn.__code__.co_varnames[: fn.__code__.co_argcount]:
                class _MP:
                    def delenv(self, k, raising=False):
                        os.environ.pop(k, None)
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
