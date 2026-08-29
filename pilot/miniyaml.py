"""Lettore YAML minimale, stdlib-only, per il sottoinsieme scritto da questo pilot
(config/*.yaml generati da entities.py e sources.py). Non e' un parser YAML generico:
niente PyYAML per restare a 2 dipendenze totali (feedparser, trafilatura).
"""
import json


def _parse_scalar(tok):
    tok = tok.strip()
    if tok.startswith('"'):
        end = tok.rindex('"')
        return json.loads(tok[: end + 1])
    if "#" in tok:
        tok = tok.split("#", 1)[0].strip()
    if tok in ("", "null"):
        return None
    if tok == "true":
        return True
    if tok == "false":
        return False
    if tok == "[]":
        return []
    try:
        return int(tok)
    except ValueError:
        pass
    try:
        return float(tok)
    except ValueError:
        pass
    return tok


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def load(path_or_text, is_text=False):
    text = path_or_text if is_text else open(path_or_text, encoding="utf-8").read()
    lines = [l for l in text.split("\n") if l.strip() and not l.strip().startswith("#")]
    pos = [0]

    def parse_block(min_indent):
        if pos[0] >= len(lines) or _indent(lines[pos[0]]) < min_indent:
            return None
        is_list = lines[pos[0]].strip().startswith("- ")
        if is_list:
            result = []
            while pos[0] < len(lines) and _indent(lines[pos[0]]) >= min_indent \
                    and lines[pos[0]].strip().startswith("- "):
                item_indent = _indent(lines[pos[0]])
                content = lines[pos[0]].strip()[2:]
                pos[0] += 1
                if ":" in content:
                    obj = {}
                    key, _, val = content.partition(":")
                    val = val.strip()
                    obj[key.strip()] = parse_block(item_indent + 2) if val == "" else _parse_scalar(val)
                    while pos[0] < len(lines) and _indent(lines[pos[0]]) == item_indent + 2 \
                            and not lines[pos[0]].strip().startswith("- "):
                        k2, _, v2 = lines[pos[0]].strip().partition(":")
                        v2 = v2.strip()
                        pos[0] += 1
                        obj[k2.strip()] = parse_block(item_indent + 4) if v2 == "" else _parse_scalar(v2)
                    result.append(obj)
                else:
                    result.append(_parse_scalar(content))
            return result
        obj = {}
        base_indent = _indent(lines[pos[0]])
        while pos[0] < len(lines) and _indent(lines[pos[0]]) == base_indent:
            key, _, val = lines[pos[0]].strip().partition(":")
            val = val.strip()
            pos[0] += 1
            obj[key.strip()] = parse_block(base_indent + 2) if val == "" else _parse_scalar(val)
        return obj

    return parse_block(0) or {}
