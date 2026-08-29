"""Genera config/entities.yaml leggendo dashboard-config.js (non lo modifica).

dashboard-config.js e' fuori scope per la scrittura: qui viene solo letto con un
mini-parser di letterali JS (stringhe/oggetti/array), sufficiente per le chiamate
c('key','label','meta',{...}) che compongono le 54 card. Niente motore JS, niente
nuova dipendenza.
"""
import json
import re
from pathlib import Path

from pilot import miniyaml
from pilot.util import has_cyrillic, lat_to_cyr, normalize_search

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_CONFIG = ROOT / "dashboard-config.js"
ENTITIES_YAML = ROOT / "config" / "entities.yaml"
TOPICS_YAML = ROOT / "config" / "topics.yaml"

_DECORATIVE_MARKS = {"•", "#", "↔", "✓", "↑"}


def load_weak_keywords():
    """§1a — dizionario di dominio politico (config/topics.yaml), normalizzato per il match."""
    if not TOPICS_YAML.exists():
        return set()
    doc = miniyaml.load(TOPICS_YAML)
    return {normalize_search(t) for t in (doc.get("weak_keywords") or [])}


def load_entities_yaml():
    if not ENTITIES_YAML.exists():
        return []
    return miniyaml.load(ENTITIES_YAML).get("entities", [])


def _skip_ws_and_string(text, i):
    """Se text[i] apre una stringa, ritorna l'indice subito dopo la stringa; altrimenti i."""
    q = text[i]
    if q not in "'\"":
        return i
    j = i + 1
    while j < len(text):
        if text[j] == "\\":
            j += 2
            continue
        if text[j] == q:
            return j + 1
        j += 1
    raise ValueError("stringa non terminata")


def extract_balanced_call(text, open_paren_idx):
    """Dato l'indice di '(' subito dopo 'c', ritorna (contenuto_argomenti, indice_dopo_chiusura)."""
    depth = 0
    i = open_paren_idx
    start_args = open_paren_idx + 1
    while i < len(text):
        ch = text[i]
        if ch in "'\"":
            i = _skip_ws_and_string(text, i)
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return text[start_args:i], i + 1
        i += 1
    raise ValueError("parentesi non bilanciate")


def top_level_split(s, sep=","):
    parts = []
    depth = 0
    cur = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in "'\"":
            j = _skip_ws_and_string(s, i)
            cur.append(s[i:j])
            i = j
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        i += 1
    if cur or parts:
        parts.append("".join(cur))
    return [p for p in (p.strip() for p in parts) if p != ""]


def _unescape_js_string(tok):
    q = tok[0]
    inner = tok[1:-1]
    out = []
    i = 0
    while i < len(inner):
        if inner[i] == "\\" and i + 1 < len(inner):
            nxt = inner[i + 1]
            out.append({"n": "\n", "t": "\t", "\\": "\\", "'": "'", '"': '"'}.get(nxt, nxt))
            i += 2
        else:
            out.append(inner[i])
            i += 1
    return "".join(out)


class NonLiteral:
    """Segna un'espressione JS non letterale (es. 'ij.toLowerCase()'): la card che la contiene
    non e' una definizione statica e viene scartata da parse_c_calls."""
    def __init__(self, raw):
        self.raw = raw


def parse_js_value(tok):
    tok = tok.strip()
    if not tok:
        return None
    if tok[0] in "'\"":
        return _unescape_js_string(tok)
    if tok[0] == "{":
        inner = tok[1:-1].strip()
        obj = {}
        for entry in top_level_split(inner):
            key, _, val = entry.partition(":")
            key = key.strip().strip("'\"")
            obj[key] = parse_js_value(val)
        return obj
    if tok[0] == "[":
        inner = tok[1:-1].strip()
        return [parse_js_value(v) for v in top_level_split(inner)]
    if tok == "true":
        return True
    if tok == "false":
        return False
    if tok == "null":
        return None
    if re.fullmatch(r"-?\d+\.\d+", tok):
        return float(tok)
    if re.fullmatch(r"-?\d+", tok):
        return int(tok)
    return NonLiteral(tok)  # identificatore/espressione non letterale (es. dentro il template IJ)


def parse_c_calls(js_text):
    """Trova tutte le chiamate letterali c('key','label','meta', {opts}) nel file."""
    cards = []
    for m in re.finditer(r"(?<![A-Za-z0-9_.])c\(", js_text):
        # esclude la dichiarazione "function c(key, label, meta, opts) {"
        preceding = js_text[max(0, m.start() - 12):m.start()]
        if preceding.rstrip().endswith("function"):
            continue
        open_idx = m.end() - 1
        try:
            args_str, _end = extract_balanced_call(js_text, open_idx)
        except ValueError:
            continue
        args = top_level_split(args_str)
        if len(args) < 2:
            continue
        try:
            values = [parse_js_value(a) for a in args]
        except Exception:
            continue
        # Scarta le chiamate con argomenti non letterali (es. il template IJ: 'ij.toLowerCase()')
        if any(isinstance(v, NonLiteral) for v in values[:4]):
            continue
        if any(v is None for v in values[:2]):
            continue
        key, label = values[0], values[1]
        meta = values[2] if len(values) > 2 and isinstance(values[2], str) else ""
        opts = values[3] if len(values) > 3 and isinstance(values[3], dict) else {}
        cards.append({
            "key": key, "label": label, "meta": meta,
            "mark": opts.get("mark", "•"),
            "type": opts.get("type", "actor"),
            "ij": opts.get("ij"),
            "keywords": opts.get("keywords") or [],
            "modules": opts.get("modules") or [],
            "requireAny": bool(opts.get("requireAny", False)),
        })
    return cards


def parse_ij_names(js_text):
    m = re.search(r"var\s+IJ_NAMES\s*=\s*(\{.*?\});", js_text, re.S)
    if not m:
        return {}
    return parse_js_value(m.group(1))


def build_territory_cards(ij_names):
    """Ricostruisce le 9 card IJ generate dinamicamente nel .map() (non letterali, quindi non
    prese da parse_c_calls) applicando la stessa logica presente in dashboard-config.js."""
    cards = []
    for idx, ij in enumerate(ij_names.keys()):
        cards.append({
            "key": ij.lower(), "label": f"{ij} · {ij_names[ij]}", "meta": "NSRS · izborna jedinica",
            "mark": ij, "type": "territory", "ij": ij,
            "keywords": [], "modules": ["IJ"], "requireAny": False,
        })
    return cards


def classify_alias(alias):
    """§1b — tre classi, non due:
    'frase'   multi-parola (es. "Predsjedništvo BiH"): matcha solo come sequenza contigua.
    'ambiguo' singola parola corta (<=4 lettere, es. US/SP/NF/BiH/RS): sola non basta, serve
              co-occorrenza con un hit forte/frase o 2 termini del dizionario politico.
    'forte'   tutto il resto: matcha da sola, un solo soggetto basta per un articolo valido.
    Il case NON conta piu' per la soglia (a differenza della vecchia is_short_ambiguous):
    'BiH' e' ambiguo tanto quanto 'US', maiuscolo o no."""
    if re.search(r"\s", alias.strip()):
        return "frase"
    letters = re.sub(r"[^A-Za-zŠĐČĆŽšđčćžА-Яа-яЀ-ӿ]", "", alias, flags=re.UNICODE)
    if 2 <= len(letters) <= 4 and letters == alias.strip():
        return "ambiguo"
    return "forte"


# §1b, diagnosi handoff + verifica sul golden set: nomi di paese/entita'/capitale generici, non
# protagonisti specifici. Nessuna co-occorrenza li rende identificatori sicuri: compaiono in
# ogni articolo sul soggetto (sport, cultura, cronaca inclusi), indipendentemente dal tema
# politico. Esclusi dagli alias, non solo declassati ad ambiguo. 'Vučić' (persona reale) resta
# alias 'beograd' valido; 'Srbija'/'Beograd' (il paese/la capitale) no.
_GEOGRAPHIC_STOPLIST = {"bih", "rs", "srbija", "beograd"}


def build_alias_entries(card, mark_counts, weak_keywords_norm):
    raw_tokens = list(card["keywords"]) + list(card["modules"])
    # mark e' un badge UI (spesso condiviso da tutte le card di uno stesso partito, es. 'US' su
    # 15 card diverse): usabile come alias SOLO quando e' univoco nel registro, altrimenti un
    # mention generico (es. "US Open" in un articolo sportivo) farebbe match su decine di entita'.
    if card["mark"] not in _DECORATIVE_MARKS and mark_counts.get(card["mark"], 0) == 1:
        raw_tokens.append(card["mark"])
    seen = set()
    aliases = []
    for tok in raw_tokens:
        if not tok or not re.search(r"[A-Za-zŠĐČĆŽšđčćžА-Яа-я]{2,}", tok):
            continue
        if tok in seen:
            continue
        # §1b: termini tematici generici (mandat, finansiranje, kompenzacion, skener...) non sono
        # identificatori di entita', vanno solo nel dizionario del filtro di rilevanza (§1a).
        tok_norm = normalize_search(tok)
        if tok_norm in weak_keywords_norm or tok_norm in _GEOGRAPHIC_STOPLIST:
            continue
        seen.add(tok)
        entry = {
            "text": tok,
            "script": "cyrl" if has_cyrillic(tok) else "latn",
            "alias_class": classify_alias(tok),
            "exact_word_uppercase": classify_alias(tok) == "ambiguo",
            "norm": normalize_search(tok),
        }
        aliases.append(entry)
        if not has_cyrillic(tok):
            cyr = lat_to_cyr(tok)
            if cyr != tok and cyr not in seen:
                seen.add(cyr)
                aliases.append({
                    "text": cyr, "script": "cyrl",
                    "alias_class": classify_alias(cyr),
                    "exact_word_uppercase": classify_alias(cyr) == "ambiguo",
                    "norm": normalize_search(cyr),
                })
    return aliases


def generate_entities():
    js_text = DASHBOARD_CONFIG.read_text(encoding="utf-8")
    ij_names = parse_ij_names(js_text)
    cards = parse_c_calls(js_text) + build_territory_cards(ij_names)
    weak_keywords_norm = load_weak_keywords()

    mark_counts = {}
    for card in cards:
        if card["mark"] not in _DECORATIVE_MARKS:
            mark_counts[card["mark"]] = mark_counts.get(card["mark"], 0) + 1

    entities = []
    for card in cards:
        entities.append({
            "key": card["key"],
            "label": card["label"],
            "type": card["type"],
            "ij": card["ij"],
            "aliases": build_alias_entries(card, mark_counts, weak_keywords_norm),
        })
    return entities, ij_names


def to_yaml_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def dump_yaml(entities, ij_names):
    """Serializzatore YAML minimale (stdlib-only): la struttura e' fissa e nota, non serve un parser generico."""
    lines = [
        "# generato da pilot/entities.py — NON modificare a mano.",
        "# fonte: dashboard-config.js (letto, non modificato). Rilanciare lo script per rigenerare.",
        f"source_of_truth: dashboard-config.js",
        f"generated_entities: {len(entities)}",
        "entities:",
    ]
    for e in entities:
        lines.append(f"  - key: {to_yaml_scalar(e['key'])}")
        lines.append(f"    label: {to_yaml_scalar(e['label'])}")
        lines.append(f"    type: {to_yaml_scalar(e['type'])}")
        lines.append(f"    ij: {to_yaml_scalar(e['ij'])}")
        if not e["aliases"]:
            lines.append("    aliases: []")
        else:
            lines.append("    aliases:")
            for a in e["aliases"]:
                lines.append(f"      - text: {to_yaml_scalar(a['text'])}")
                lines.append(f"        script: {to_yaml_scalar(a['script'])}")
                lines.append(f"        norm: {to_yaml_scalar(a['norm'])}")
                lines.append(f"        alias_class: {to_yaml_scalar(a['alias_class'])}")
                lines.append(f"        exact_word_uppercase: {to_yaml_scalar(a['exact_word_uppercase'])}")
    lines.append("ij_names:")
    for ij, name in ij_names.items():
        lines.append(f"  {ij}: {to_yaml_scalar(name)}")
    return "\n".join(lines) + "\n"


# --- matching (§1b) e filtro di rilevanza (§1a), condivisi da dedup.py e score.py --------------

_WORD_RE_CACHE = {}
_LEFT_RE_CACHE = {}


def _exact_word_match(alias_text, raw_text):
    """Confine di parola pieno, case esatto: per la classe 'ambiguo' (US, SP, BiH, RS...),
    che in serbo non si declina come alias istituzionale invariante."""
    rx = _WORD_RE_CACHE.get(alias_text)
    if rx is None:
        rx = re.compile(r"(?<!\w)" + re.escape(alias_text) + r"(?!\w)")
        _WORD_RE_CACHE[alias_text] = rx
    return bool(rx.search(raw_text))


def _left_boundary_match(alias_norm, norm_text):
    """Confine solo a sinistra, su testo normalizzato: per 'forte'/'frase', tollera le desinenze
    di caso del serbo (Стевандић/Стевандића/Стевандићу condividono lo stesso prefisso normalizzato)
    ma impedisce match a meta' parola (§1b: 'senza \\b, US matcha dentro usvojen'). Il trattino
    NON e' un confine valido: senza escluderlo, 'добој' matcha dentro l'aggettivo composto
    'зеничко-добојског' (Zenica-Doboj), non la citta' Добој."""
    rx = _LEFT_RE_CACHE.get(alias_norm)
    if rx is None:
        rx = re.compile(r"(?<![\w-])" + re.escape(alias_norm))
        _LEFT_RE_CACHE[alias_norm] = rx
    return bool(rx.search(norm_text))


def count_weak_keywords(text_norm, weak_keywords_norm):
    return sum(1 for kw in weak_keywords_norm if kw and _left_boundary_match(kw, text_norm))


def match_entities(title, text, entities, weak_keywords_norm=None):
    """exact -> alias -> normalizzato senza diacritici -> cirillico. Niente fuzzy (§1b).
    Gli hit di classe 'ambiguo' sopravvivono solo se nell'item c'e' anche un hit forte/frase
    (di qualunque entita'), o almeno 2 termini del dizionario politico nel corpo."""
    weak_keywords_norm = weak_keywords_norm or set()
    title_norm = normalize_search(title)
    text_norm = normalize_search(text)
    lead_norm = normalize_search(text[:300])
    has_two_weak = count_weak_keywords(text_norm, weak_keywords_norm) >= 2

    strong_hits, ambiguous_hits = [], []
    for ent in entities:
        found_in = None
        matched_class = None
        for alias in ent["aliases"]:
            cls = alias.get("alias_class", "forte")
            if cls == "ambiguo":
                if _exact_word_match(alias["text"], title):
                    found_in, matched_class = "title", cls
                    break
                if _exact_word_match(alias["text"], text[:300]):
                    found_in = found_in or "lead"
                    matched_class = matched_class or cls
                if _exact_word_match(alias["text"], text):
                    found_in = found_in or "body"
                    matched_class = matched_class or cls
                    break
            else:
                if alias["norm"] and _left_boundary_match(alias["norm"], title_norm):
                    found_in, matched_class = "title", cls
                    break
                if alias["norm"] and _left_boundary_match(alias["norm"], lead_norm):
                    found_in = found_in or "lead"
                    matched_class = matched_class or cls
                if alias["norm"] and _left_boundary_match(alias["norm"], text_norm):
                    found_in = found_in or "body"
                    matched_class = matched_class or cls
                    break
        if found_in:
            centrality = {"title": 1.0, "lead": 0.6, "body": 0.3}[found_in]
            hit = {"key": ent["key"], "label": ent["label"], "centrality": centrality, "alias_class": matched_class}
            (ambiguous_hits if matched_class == "ambiguo" else strong_hits).append(hit)

    if ambiguous_hits and (strong_hits or has_two_weak):
        strong_hits.extend(ambiguous_hits)
    return strong_hits


def is_relevant(hits, text, weak_keywords_norm):
    """§1a — filtro di rilevanza politica: un alias forte/frase basta da solo, altrimenti
    servono almeno 2 termini del dizionario politico."""
    if any(h.get("alias_class") != "ambiguo" for h in hits):
        return True
    return count_weak_keywords(normalize_search(text), weak_keywords_norm) >= 2


def main():
    entities, ij_names = generate_entities()
    ENTITIES_YAML.parent.mkdir(parents=True, exist_ok=True)
    ENTITIES_YAML.write_text(dump_yaml(entities, ij_names), encoding="utf-8", newline="\n")
    print(f"config/entities.yaml scritto: {len(entities)} entita'")
    return entities


if __name__ == "__main__":
    main()
