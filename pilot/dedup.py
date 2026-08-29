"""§5 — Dedup (stesso articolo) e clustering (stesso evento). Regole, niente LLM.

Dedup (§2b), in ordine: URL canonico identico -> content_hash -> similarita' del corpo (TF-IDF +
coseno, §C1) entro 48h -> title_norm molto simile (fallback per corpo troncato o estratto male).
Clustering (§2c): prove multiple con centroide di cluster, entro finestra 48-72h
(config/scoring.yaml), unione transitiva (A~B~C -> un cluster anche se A non~C).

TASK_BETA_02 §C1, 2026-08-28: la prova di corpo era Jaccard su shingle di 4-grammi di caratteri.
Bocciata con evidenza — non normalizzata per lunghezza, un sommario RSS di poche righe non puo'
somigliare all'articolo pieno che racconta lo stesso evento (RFC_SECONDA_OPINIONE_02.md §5.1/§8).
Sostituita con TF-IDF (tf logaritmico, idf sul corpus, L2) + coseno: la norma del vettore assorbe
la lunghezza. Vedi TASK_BETA_02_RESULTS.md per la calibrazione (162 coppie golden, separata per
dedup e clustering — le due prove NON condividono soglia, coseno separa "stesso articolo" da
"stesso evento diverso testo" con margini diversi).
"""
import json
import math
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from pilot import miniyaml
from pilot.entities import is_relevant, load_entities_yaml, load_weak_keywords, match_entities

# §2c: solo le persone nominate (type:'actor') sono un segnale sicuro di "stesso evento" quando
# condivise. Ogni altro tipo e' troppo largo: 'territory'/'race'/'external' coprono un'intera
# regione/competizione (es. 'ij5-konkurencija'), 'party'/'institution' coprono un intero partito
# o ente (es. 'SNSD', 'CIK') citato in decine di articoli scorrelati nella stessa settimana
# elettorale. Condividerne 2 fondeva prima 13, poi 10 articoli scorrelati in un cluster solo
# (verificato sul corpus reale, non solo sui test sintetici).
_CLUSTERING_ENTITY_TYPES = {"actor"}

# soglia minima di corpus perche' la document frequency delle entita' sia una misura e non rumore
# (vedi max_document_frequency in cluster()). C2, TASK_BETA_02, 2026-08-28: NON e' una soglia da
# calibrare su un golden set - e' una guardia strutturale ("sotto N documenti una percentuale non
# vuol dire niente"), dichiarata cosi' invece di far finta di misurarla su dati che non bastano.
_MIN_ITEMS_FOR_DF = 50

ROOT = Path(__file__).resolve().parent.parent
CLEAN_JSONL = ROOT / "data" / "clean.jsonl"
ITEMS_JSONL = ROOT / "data" / "items.jsonl"
CLUSTERS_JSONL = ROOT / "data" / "clusters.jsonl"
SCORING_YAML = ROOT / "config" / "scoring.yaml"

TITLE_SIM_THRESHOLD_DEDUP = 0.90
DEDUP_WINDOW_HOURS = 48
# TASK_BETA_02 C1, 2026-08-28: TF-IDF+coseno su 162 coppie golden (44 DUPLICATO/7 STESSO_EVENTO/
# 111 DIVERSI, incl. le coppie contaminate da BL_IJ3_006 - resta nella pipeline finche' il bug di
# estrazione non e' corretto, vedi TASK_BETA_02_RESULTS.md). DUPLICATO vs resto: F1 0.977
# (prec 0.977, rec 0.977) a 0.80 sull'intero campione. Soglia piu' alta della clustering di
# proposito: qui un falso positivo fonde due articoli distinti in un item solo (distruttivo).
BODY_SIM_THRESHOLD_DEFAULT = 0.80


def load_clean():
    items = []
    with open(CLEAN_JSONL, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    return items


def _dt(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def _hours_between(a, b):
    if a is None or b is None:
        return None
    return abs((a - b).total_seconds()) / 3600.0


def build_idf(items, field="text_norm"):
    """idf sul corpus passato: log(N/df), N = documenti col campo non vuoto. Nessuna dipendenza:
    tf logaritmico + questo idf + L2 e' tutto quello che serve per il coseno sotto."""
    df = Counter()
    n = 0
    for it in items:
        terms = set((it.get(field) or "").split())
        if not terms:
            continue
        n += 1
        df.update(terms)
    return {"_n": n, "_df": df}


def tfidf_vector(text, idf):
    """tf logaritmico (1+log conteggio) * idf, normalizzato L2. Termini assenti dal corpus di
    riferimento (idf) sono ignorati: non hanno un peso calcolabile."""
    n, df = idf["_n"], idf["_df"]
    tf = Counter((text or "").split())
    vec = {}
    for term, count in tf.items():
        d = df.get(term, 0)
        if d == 0:
            continue
        vec[term] = (1.0 + math.log(count)) * math.log(n / d) if n and d else 0.0
    norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
    return {t: w / norm for t, w in vec.items()}


def cosine(va, vb):
    if len(va) > len(vb):
        va, vb = vb, va
    return sum(w * vb.get(t, 0.0) for t, w in va.items())


def jaccard_sets(a, b):
    """Jaccard su insiemi di parole (titolo): usato solo per token_overlap/title_threshold,
    non per il corpo (vedi TF-IDF+coseno sopra)."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _group_by_pass(items, remaining, used, groups, key_fn):
    """Passaggio a chiave esatta (URL canonico, hash): raggruppa gli indici che condividono
    la stessa chiave non vuota."""
    by_key = {}
    for i in remaining:
        key = key_fn(items[i])
        if not key:
            continue
        by_key.setdefault(key, []).append(i)
    for idxs in by_key.values():
        if len(idxs) > 1:
            groups.append(idxs)
            for i in idxs:
                used[i] = True
    return [i for i in range(len(items)) if not used[i]]


def dedup(items, body_sim_threshold=BODY_SIM_THRESHOLD_DEFAULT, idf=None):
    """§2b — cascata: URL canonico identico -> content_hash -> similarita' del corpo (TF-IDF +
    coseno, §C1, entro 48h) -> titolo molto simile (fallback). Ritorna una lista di gruppi
    (liste di indici), il primo item di ogni gruppo e' il piu' vecchio (deciso da build_deduped_items)."""
    if idf is None:
        idf = build_idf(items)
    groups = []
    used = [False] * len(items)

    remaining = _group_by_pass(items, list(range(len(items))), used, groups, lambda it: it.get("final_url"))
    remaining = _group_by_pass(items, remaining, used, groups, lambda it: it["content_hash"])

    # passaggio 3: similarita' del corpo (TF-IDF + coseno) entro 48h — il criterio centrale
    # (§2b): regge variazioni di titolo e di alfabeto (text_norm e' gia' cirillico->latino).
    # O(n^2) sul residuo: pilota, non scala oltre poche migliaia di item.
    vecs_cache = {i: tfidf_vector(items[i]["text_norm"], idf) for i in remaining}
    remaining_sorted = sorted(remaining, key=lambda i: items[i].get("published_at") or "")
    for a_pos, i in enumerate(remaining_sorted):
        if used[i]:
            continue
        group = [i]
        dt_i = _dt(items[i].get("published_at"))
        for j in remaining_sorted[a_pos + 1:]:
            if used[j]:
                continue
            dt_j = _dt(items[j].get("published_at"))
            hrs = _hours_between(dt_i, dt_j)
            if hrs is not None and hrs > DEDUP_WINDOW_HOURS:
                continue
            sim = cosine(vecs_cache[i], vecs_cache[j])
            if sim >= body_sim_threshold:
                group.append(j)
                used[j] = True
        if len(group) > 1:
            used[i] = True
            groups.append(group)

    remaining = [i for i in range(len(items)) if not used[i]]

    # passaggio 4: titolo molto simile entro 48h — fallback per corpo troncato/estratto male,
    # dove il passaggio 3 non basta da solo.
    # RFC_SECONDA_OPINIONE_02.md §6: i gruppi dei passaggi 1-3 restavano chiusi ai membri trovati
    # solo qui (titolo quasi identico, corpo troppo diverso o troncato per il passaggio 3): 10-12
    # coppie a title_norm identico misurate come item distinti nonostante il fallback esistesse.
    # Un residuo ora prova prima ad agganciarsi a un gruppo gia' formato, confrontato contro i
    # suoi membri ORIGINALI (snapshot presa prima del passaggio, non i membri aggiunti qui): evita
    # catene titolo-a-titolo su piu' hop dentro questo stesso passaggio. Il confronto fra residui
    # resta come prima, solo contro l'ancora i (stesso comportamento di sempre).
    def _title_match(i, j):
        hrs = _hours_between(_dt(items[i].get("published_at")), _dt(items[j].get("published_at")))
        if hrs is not None and hrs > DEDUP_WINDOW_HOURS:
            return False
        return SequenceMatcher(None, items[i]["title_norm"], items[j]["title_norm"]).ratio() >= TITLE_SIM_THRESHOLD_DEDUP

    frozen_groups = [(g, list(g)) for g in groups]
    remaining_sorted = sorted(remaining, key=lambda i: items[i].get("published_at") or "")
    for i in remaining_sorted:
        if used[i]:
            continue
        for g, snapshot in frozen_groups:
            if any(_title_match(i, m) for m in snapshot):
                g.append(i)
                used[i] = True
                break

    remaining = [i for i in remaining_sorted if not used[i]]
    for a_pos, i in enumerate(remaining):
        if used[i]:
            continue
        group = [i]
        for j in remaining[a_pos + 1:]:
            if used[j]:
                continue
            if _title_match(i, j):
                group.append(j)
                used[j] = True
        used[i] = True
        groups.append(group)

    # Chiusura completa RFC §6: resta il caso in cui ENTRAMBI i membri di una coppia a titolo
    # identico sono gia' stati assorbiti in DUE gruppi diversi ai passaggi 1-3 (es. content_hash
    # diverso ma title_norm identico) — il residuo sopra non basta, va unito il gruppo. Indicizzato
    # per title_norm ESATTO (il caso misurato, non il ratio approssimato del fallback): economico,
    # O(n), e converge in un solo giro perche' ogni gruppo si unisce al primo che condivide il
    # titolo, mai a se stesso.
    by_exact_title = {}
    for idx, g in enumerate(groups):
        for m in g:
            by_exact_title.setdefault(items[m]["title_norm"], set()).add(idx)

    merged_away = set()
    for group_idxs in by_exact_title.values():
        idxs = sorted(gi for gi in group_idxs if gi not in merged_away)
        if len(idxs) < 2:
            continue
        keep = idxs[0]
        for other in idxs[1:]:
            if other in merged_away:
                continue
            if not any(_title_match(a, b) for a in groups[keep] for b in groups[other]):
                continue
            groups[keep].extend(groups[other])
            groups[other] = []
            merged_away.add(other)

    return [g for g in groups if g]


def build_deduped_items(items, groups):
    """Un gruppo -> un item, con duplicates[] = url degli altri ed evidence[] per ognuno."""
    out = []
    for idxs in groups:
        members = [items[i] for i in idxs]
        members.sort(key=lambda it: it.get("published_at") or "9999")
        primary = members[0]
        evidence = [
            {"source_id": m["source_id"], "url": m["url"], "published_at": m.get("published_at"), "evidence_type": "article"}
            for m in members
        ]
        merged = dict(primary)
        merged["duplicates"] = [m["url"] for m in members[1:]]
        merged["evidence"] = evidence
        merged["n_copies"] = len(members)
        merged["source_ids"] = sorted({m["source_id"] for m in members})
        out.append(merged)
    return out


def load_scoring_config():
    if SCORING_YAML.exists():
        return miniyaml.load(SCORING_YAML)
    return {}


def token_overlap(a, b):
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _entity_keys(item, clustering_types=None):
    keys = {h["key"] for h in (item.get("_entity_hits") or [])}
    if clustering_types is None:
        return keys
    return {k for k in keys if clustering_types.get(k) in _CLUSTERING_ENTITY_TYPES}


def cluster(deduped_items, scoring_cfg, idf=None):
    """§2c — stesso evento, prove multiple invece di un singolo test: entita' condivise (>=2),
    TF-IDF+coseno del corpo sopra soglia (§C1), parole informative condivise nel titolo (una
    qualunque basta, non serve che passino tutte e tre). Il cluster accumula una rappresentazione
    propria contro cui si confronta ogni nuovo candidato, non solo il primo articolo: risolve la
    transitivita' (A~B~C -> un cluster anche se A non~C). Le entita' si uniscono per davvero
    (vocabolario piccolo e discreto, l'unione resta precisa); corpo e titolo NO — un pool di
    vettori/token che cresce con articoli politici in serbo finisce per somigliare a qualunque
    nuovo articolo per lessico condiviso, non per argomento (verificato: causava cluster da 13
    item sul corpus reale). Corpo e titolo si confrontano quindi contro il MASSIMO sui singoli
    membri (single-linkage)."""
    if idf is None:
        idf = build_idf(deduped_items)
    clustering_cfg = scoring_cfg.get("clustering") or {}
    window_hours = clustering_cfg.get("window_hours")
    window_hours = 60 if window_hours is None else window_hours
    title_threshold = clustering_cfg.get("title_overlap_threshold")
    title_threshold = 0.35 if title_threshold is None else title_threshold
    # TASK_BETA_02 C1, 2026-08-28: TF-IDF+coseno, non piu' Jaccard su shingle. Calibrato su 110
    # coppie golden ESCLUSA la fonte contaminata BL_IJ3_006 (vedi TASK_BETA_02_RESULTS.md): F1
    # 0.968 stabile su tutto il plateau 0.10-0.40, scelto 0.20 al centro. Includendo BL_IJ3_006
    # (bug di estrazione non ancora corretto) il coseno resta piu' robusto del Jaccard ma non
    # immune: qualche falso accorpamento su quella fonte e' un rischio noto, non nuovo.
    body_threshold = clustering_cfg.get("body_overlap_threshold")
    body_threshold = 0.20 if body_threshold is None else body_threshold
    min_shared_entities = clustering_cfg.get("min_shared_entities")
    min_shared_entities = 2 if min_shared_entities is None else min_shared_entities
    type_by_key = {e["key"]: e["type"] for e in load_entities_yaml()}

    # B4a: il filtro per tipo qui sopra non basta. Un'entita' presente in una grossa fetta del
    # corpus non distingue un evento da un altro: e' document frequency, non prova di "stesso
    # evento". Con l'aggiunta di 'dodik' (28.1% degli item rilevanti) accanto a 'minic' (15.7%)
    # bastavano quelle due entita' condivise per fondere 18 articoli e TRE eventi distinti
    # (commemorazione Mladic + Kocicev zbor + sentenza Jahorina) in un cluster solo, che finiva
    # primo nel radar con signal_score 13.1. Stesso ragionamento dei tipi larghi, ma misurato.
    # Sotto _MIN_ITEMS_FOR_DF la frequenza non e' misurabile: su 3 documenti "presente nel 67% del
    # corpus" non dice niente sul potere discriminante, e spegnerebbe il segnale entita' proprio
    # dove serve (batch piccoli, test sintetici). Il filtro si attiva solo su corpus reali.
    max_df = clustering_cfg.get("max_document_frequency")
    max_df = 0.10 if max_df is None else max_df  # gap netto nel corpus: 28% / 16% poi 7.6%
    if len(deduped_items) >= _MIN_ITEMS_FOR_DF and max_df:
        df = {}
        for it in deduped_items:
            for k in {h["key"] for h in (it.get("_entity_hits") or [])}:
                df[k] = df.get(k, 0) + 1
        for k, n in df.items():
            if n / len(deduped_items) > max_df:
                type_by_key.pop(k, None)

    items_sorted = sorted(range(len(deduped_items)), key=lambda i: deduped_items[i].get("published_at") or "")
    clusters = []  # ognuno: {"members":[idx,...], "member_shingles":[set,...], "member_tokens":[set,...], "entities":set, "last_dt":datetime|None}

    for i in items_sorted:
        it = deduped_items[i]
        dt_i = _dt(it.get("published_at"))
        vec_i = tfidf_vector(it.get("text_norm", ""), idf)
        entities_i = _entity_keys(it, type_by_key)
        tokens_i = set(it.get("title_norm", "").split())

        best, best_score = None, -1.0
        for c in clusters:
            hrs = _hours_between(dt_i, c["last_dt"])
            if hrs is not None and hrs > window_hours:
                continue
            shared_entities = len(entities_i & c["entities"])
            body_sim = max((cosine(vec_i, v) for v in c["member_vecs"]), default=0.0)
            token_sim = max((jaccard_sets(tokens_i, t) for t in c["member_tokens"]), default=0.0)
            matches = shared_entities >= min_shared_entities or body_sim >= body_threshold or token_sim >= title_threshold
            if not matches:
                continue
            score = shared_entities + body_sim + token_sim
            if score > best_score:
                best, best_score = c, score

        if best is not None:
            best["members"].append(i)
            best["member_vecs"].append(vec_i)
            best["member_tokens"].append(tokens_i)
            best["entities"] |= entities_i
            if dt_i and (best["last_dt"] is None or dt_i > best["last_dt"]):
                best["last_dt"] = dt_i
        else:
            clusters.append({"members": [i], "member_vecs": [vec_i], "member_tokens": [tokens_i],
                              "entities": entities_i, "last_dt": dt_i})

    cluster_records = []
    for n, c in enumerate(clusters, start=1):
        members = [deduped_items[i] for i in c["members"]]
        members.sort(key=lambda it: it.get("published_at") or "9999")
        cluster_id = f"CL-{datetime.now(timezone.utc).year}-{n:04d}"
        for m in members:
            m["cluster_id"] = cluster_id
        cluster_records.append({
            "cluster_id": cluster_id,
            "first_published_at": members[0].get("published_at"),
            "occurred_at": None,
            "items": [m["raw_id"] for m in members],
            "sources": sorted({sid for m in members for sid in m["source_ids"]}),
            "entities": [],  # popolato da score.py dopo l'entity matching
            "evidence_count": sum(m["n_copies"] for m in members),
        })
    return cluster_records


def apply_relevance_filter(deduped_items):
    """§1a — entity matching + filtro di rilevanza, PRIMA del clustering: gli item scartati
    restano in archivio (items.jsonl) ma non generano cluster. Attacca modules/_entity_hits/
    is_relevant su ogni item (score.py li riusa, non li ricalcola)."""
    entities = load_entities_yaml()
    weak_keywords_norm = load_weak_keywords()
    relevant, dropped = [], []
    for it in deduped_items:
        hits = match_entities(it.get("title", ""), it.get("text", ""), entities, weak_keywords_norm)
        it["modules"] = sorted({h["key"] for h in hits})
        it["_entity_hits"] = hits
        text_for_filter = it.get("title", "") + " " + it.get("text", "")
        relevant_flag = is_relevant(hits, text_for_filter, weak_keywords_norm)
        it["is_relevant"] = relevant_flag
        (relevant if relevant_flag else dropped).append(it)
    return relevant, dropped


def run():
    items = load_clean()
    scoring_cfg = load_scoring_config()
    body_sim_threshold = (scoring_cfg.get("dedup") or {}).get("body_similarity_threshold")
    body_sim_threshold = BODY_SIM_THRESHOLD_DEFAULT if body_sim_threshold is None else body_sim_threshold
    # idf calcolato una volta sull'intero corpus pulito: stessa base di riferimento per dedup (§2b)
    # e clustering (§2c), coerente con la calibrazione in TASK_BETA_02_RESULTS.md.
    idf = build_idf(items)
    groups = dedup(items, body_sim_threshold=body_sim_threshold, idf=idf)
    deduped = build_deduped_items(items, groups)
    relevant, dropped = apply_relevance_filter(deduped)
    clusters = cluster(relevant, scoring_cfg, idf=idf)

    with open(ITEMS_JSONL, "w", encoding="utf-8") as f:
        for it in deduped:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    with open(CLUSTERS_JSONL, "w", encoding="utf-8") as f:
        for c in clusters:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"raw puliti: {len(items)} -> item dopo dedup: {len(deduped)} (rapporto {len(items)}/{len(deduped)})")
    print(f"filtro rilevanza (§1a): {len(relevant)} rilevanti, {len(dropped)} scartati "
          f"({len(dropped) * 100 // len(deduped) if deduped else 0}% del corpus)")
    print(f"item rilevanti: {len(relevant)} -> cluster: {len(clusters)} (rapporto {len(relevant)}/{len(clusters) or 1})")
    return deduped, clusters


if __name__ == "__main__":
    run()
