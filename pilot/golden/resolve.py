"""Ponte FIX_00 -> FIX_01: collassa le coppie a/b + decisione umana di golden_dataset.json
in un'unica etichetta finale per item (is_political, entities_attese) e deriva duplicate_of/
cluster_atteso con union-find sulle coppie giudicate. Riscrive golden_dataset.json aggiungendo
questi campi, senza toccare quelli di FIX_00 (a/b/label_source/models_agreed restano intatti).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_JSON = ROOT / "data" / "golden" / "golden_dataset.json"


def resolve_annotation(item):
    """Ritorna (is_political, entities) risolti, o None se lo skip umano non permette di decidere."""
    if item["label_source"] in ("AGREED", "AGREED_SPOT_CHECKED"):
        return item["a"]["is_political"], item["a"]["entities"]
    override = item.get("human_override")
    if override == "SKIPPED":
        return None
    choice = override or item.get("human_decision")
    if choice == "OTHER":
        return None  # nessun caso reale in questo golden set (verificato: 0 decisioni OTHER)
    side = item["a"] if choice == "A" else item["b"]
    return side["is_political"], side["entities"]


def resolve_pair_label(pair):
    if pair["label_source"] in ("AGREED", "AGREED_SPOT_CHECKED"):
        return pair["a"]["label"]
    override = pair.get("human_override")
    if override == "SKIPPED":
        return None
    choice = override or pair.get("human_decision")
    if choice == "OTHER":
        return None
    side = pair["a"] if choice == "A" else pair["b"]
    return side["label"]


class UnionFind:
    def __init__(self, ids):
        self.parent = {i: i for i in ids}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def resolve():
    data = json.loads(GOLDEN_JSON.read_text(encoding="utf-8"))
    items = data["items"]
    pairs = data["pairs"]
    all_item_ids = [it["item_id"] for it in items]

    skipped_annotations = []
    for it in items:
        resolved = resolve_annotation(it)
        if resolved is None:
            skipped_annotations.append(it["item_id"])
            it["resolved_is_political"] = None
            it["resolved_entities"] = None
        else:
            it["resolved_is_political"], it["resolved_entities"] = resolved

    # union-find su TUTTI i raw_id che compaiono in una coppia, non solo i 100 annotati: le 50
    # coppie negative campionate da pairs.py pescano dall'intero corpus di 245 item puliti, non
    # solo dal campione annotato (bug trovato: scartava silenziosamente 42/58 coppie prima di
    # scrivere resolved_label, perche' l'id "non annotato" non era nell'union-find).
    all_pair_ids = {rid for p in pairs for rid in p["item_id"].split("__")}
    uf_ids = set(all_item_ids) | all_pair_ids
    dup_uf = UnionFind(uf_ids)
    cluster_uf = UnionFind(uf_ids)
    skipped_pairs = []
    pair_labels = {}
    for p in pairs:
        label = resolve_pair_label(p)
        pair_labels[p["item_id"]] = label
        p["resolved_label"] = label
        if label is None:
            skipped_pairs.append(p["item_id"])
            continue
        raw_a, raw_b = p["item_id"].split("__")
        if label == "DUPLICATO":
            dup_uf.union(raw_a, raw_b)
            cluster_uf.union(raw_a, raw_b)
        elif label == "STESSO_EVENTO":
            cluster_uf.union(raw_a, raw_b)

    # duplicate_of: il piu' piccolo raw_id del gruppo (escluso se stesso), null se singleton
    dup_groups = {}
    for rid in all_item_ids:
        dup_groups.setdefault(dup_uf.find(rid), []).append(rid)
    duplicate_of = {}
    for root, members in dup_groups.items():
        if len(members) == 1:
            duplicate_of[members[0]] = None
            continue
        canonical = sorted(members)[0]
        for m in members:
            duplicate_of[m] = None if m == canonical else canonical

    # cluster_atteso: id di cluster leggibile per ogni gruppo (unione DUPLICATO + STESSO_EVENTO)
    cluster_groups = {}
    for rid in all_item_ids:
        cluster_groups.setdefault(cluster_uf.find(rid), []).append(rid)
    cluster_atteso = {}
    for n, (root, members) in enumerate(sorted(cluster_groups.items(), key=lambda kv: sorted(kv[1])), start=1):
        cid = f"GOLDEN-CL-{n:03d}"
        for m in members:
            cluster_atteso[m] = cid

    for it in items:
        it["duplicate_of"] = duplicate_of.get(it["item_id"])
        it["cluster_atteso"] = cluster_atteso.get(it["item_id"])

    data["resolve_meta"] = {
        "annotazioni_skippate": skipped_annotations,
        "coppie_skippate": skipped_pairs,
        "n_cluster_attesi_non_singleton": sum(1 for members in cluster_groups.values() if len(members) > 1),
        "n_gruppi_duplicati": sum(1 for members in dup_groups.values() if len(members) > 1),
    }

    GOLDEN_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    print(f"golden_dataset.json aggiornato: {len(items)} item risolti, {len(skipped_annotations)} skip annotazione, "
          f"{len(skipped_pairs)} skip coppia")
    print(f"cluster attesi non-singleton: {data['resolve_meta']['n_cluster_attesi_non_singleton']}, "
          f"gruppi duplicati: {data['resolve_meta']['n_gruppi_duplicati']}")
    return data


if __name__ == "__main__":
    resolve()
