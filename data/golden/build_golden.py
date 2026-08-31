"""Genera data/golden/golden_dataset.json: 30 articoli scelti a mano dal corpus reale
(data/scored_items.jsonl), annotati a occhio confrontando i titoli. Script una tantum,
non fa parte della pipeline (§TEST, 'Golden set'). Rilanciare solo se il corpus raccolto cambia."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ITEMS = {json.loads(l)["raw_id"]: json.loads(l) for l in open(ROOT / "data" / "scored_items.jsonl", encoding="utf-8")}
OUT = Path(__file__).resolve().parent / "golden_dataset.json"


def rec(rid, cluster_expected=None, entities_expected=None, duplicate_expected=False, note=""):
    it = ITEMS[rid]
    return {
        "raw_id": rid, "title": it["title"], "url": it["url"], "source_id": it["source_id"],
        "published_at": it.get("published_at"),
        "cluster_id_pipeline": it.get("cluster_id"), "modules_pipeline": it["modules"],
        "cluster_expected": cluster_expected if cluster_expected is not None else it.get("cluster_id"),
        "entities_expected": entities_expected if entities_expected is not None else it["modules"],
        "duplicate_expected": duplicate_expected, "note": note,
    }


golden = []

# 4 cluster corretti (verificati a mano sui titoli): stesso evento, fonti/formulazioni diverse
correct_pairs = [
    ("ccfe382f824454b668c874c4", "53081f3639dda3aa17428ed0", "protest prevoznika ispred zgrade EU Sarajevo"),
    ("52224bbbfa0a2534f5d79fc2", "b0801ec4371aeadbb4964f53", "Minic otvorio Festival domacih proizvoda Banjaluka"),
    ("60abd8a51d523fc4e62cee90", "7b1d33f96791874fba2f566c", "izvjestaj o generalu iz Haga"),
    ("59594f9dc62119e837457cb7", "f2dc83bbd67f5b8bda12d535", "trudnica transportovana helikopterom Banjaluka"),
]
for a, b, note in correct_pairs:
    cid = ITEMS[a]["cluster_id"]
    golden.append(rec(a, cluster_expected=cid, note=f"cluster corretto: {note}"))
    golden.append(rec(b, cluster_expected=cid, note=f"cluster corretto: {note}"))

# 4 articoli sulla stessa vicenda (Vulic/GIK Doboj) che la pipeline ha messo in 4 cluster diversi:
# miss di recall reale, annotato a mano con l'evento comune atteso.
vulic_ids = ["4153f452667d0b364241bc15", "912a9f1a25114db42a205f6c", "556409eb69b5566f7a2b8d08", "280646ac7c75ecf4b90c2c1c"]
for rid in vulic_ids:
    golden.append(rec(rid, cluster_expected="GOLD-VULIC-GIK-DOBOJ",
                       note="stessa vicenda (accusa GIK Doboj), la pipeline li ha separati in 4 cluster: miss di recall"))

# 2 falsi positivi noti: articoli di tennis dove "US" (US Open) matcha entita' politiche con lo
# stesso alias "US" — limite intrinseco del matching per alias senza disambiguazione di contesto.
tennis_ids = ["844f00e228e0dacbd83f4558", "3cf645a054b57a4d08859ea7"]
for rid in tennis_ids:
    golden.append(rec(rid, entities_expected=[], note="falso positivo: 'US' (US Open tennis) matcha entita' politiche"))

# 16 item singoli, campione casuale (seed 7) gia' rivisto a mano: nessuna correzione necessaria,
# modules_pipeline confermato come entities_expected.
singles = [
    "a67015834bff2e8726e5eae9", "31116148cce6a00adcd7a786", "c10745c3794e45a317b2a4b6",
    "c2dd5e29b7f2b0b4dfb36337", "f7f14139f94de67965a9c441", "c0aa56260ddd1a4de9c71734",
    "1414c10b09132cfb53c5355c", "5aeb4402ff46514bc0d6dc1c", "d5c8bc5b3552eebec82a33b6",
    "d976cef52e95f065d3e212c3", "a4ad9dbf055c18963fe0e6b5", "8ece12a4dc7756a4380591da",
    "ffcf4534d0a343ba806cc85a", "e3b5d7b53f18b4993e0994da", "8ff17dadffd51f86fe08dadd",
    "ff308b32dd3d9a5ec6d1343c",
]
for rid in singles:
    golden.append(rec(rid, note="campione casuale, confermato a mano"))

assert len(golden) == 30, len(golden)
OUT.write_text(json.dumps(golden, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
print(f"golden_dataset.json scritto: {len(golden)} item")
