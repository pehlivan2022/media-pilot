"""Utilita' condivise: fetch HTTP, canonicalizzazione URL, date -> UTC, hash, traslitterazione sr."""
import hashlib
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

USER_AGENT = "MediaPilotBot/0.1 (research pilot; contact hotelitaliapalace@gmail.com)"

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_EXACT = {"fbclid", "gclid", "amp", "ref", "mc_cid", "mc_eid", "igshid"}


class FetchError(Exception):
    def __init__(self, kind, message, http_status=None):
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status


def fetch(url, timeout=15, retries=2, headers=None):
    """GET reale con retry/backoff. Ritorna (status:int, headers:dict, body:bytes)."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    # sitemap <loc> entries occasionally carry raw non-ASCII characters (unencoded slugs) that
    # http.client's request line can't encode as ascii and crashes the whole run (verified live,
    # 2026-08-31: '₂' from a sitemap URL killed collect() at source 22/33) - quote() with
    # '%' in safe leaves already-percent-encoded URLs untouched.
    url = quote(url, safe="%/:?&=@!$'()*+,;#~")
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=req_headers, method="GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return 304, dict(e.headers), b""
            if e.code in (429, 502, 503, 504) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            kind = "RATE_LIMIT" if e.code in (429, 502, 503, 504) else ("BLOCKED" if e.code in (401, 403) else "FETCH_ERROR")
            raise FetchError(kind, f"HTTP {e.code} {url}", e.code) from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            # ConnectionError copre http.client.RemoteDisconnected: verificato dal vivo (B1/B2a,
            # 2026-08-28) su una replay Wayback che chiude la connessione senza risposta — senza
            # questo except, un'eccezione non gestita interrompeva l'intero collect() su una
            # sola fonte instabile, invece di limitarsi a un errore loggato per quella fonte.
            last_err = e
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise FetchError("FETCH_ERROR", f"{e} {url}") from e
    raise FetchError("FETCH_ERROR", f"{last_err} {url}")


def canonicalize_url(url):
    """Rimuove tracking params, frammenti, varianti /amp, normalizza host/scheme.

    §5a: scheme/porta incoerenti (es. RTRS pubblica http://host:443/..., scheme e porta di scriptt
    diversi -> il server risponde 400). http su porta 443 diventa https senza porta esplicita,
    https su porta 80 diventa http senza porta esplicita: e' lavoro del normalizzatore URL, non
    un bug da lasciare alla fonte."""
    if not url:
        return url
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()
    if parts.port == 443 and scheme == "http":
        scheme = "https"
        netloc = parts.hostname or netloc
    elif parts.port == 80 and scheme == "https":
        scheme = "http"
        netloc = parts.hostname or netloc
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith(_TRACKING_PREFIXES) and k.lower() not in _TRACKING_EXACT
    ]
    path = parts.path
    if path.endswith("/amp/"):
        path = path[: -len("amp/")]
    elif path.endswith("/amp"):
        path = path[: -len("amp")]
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return urlunsplit((scheme, netloc, path or "/", urlencode(query), ""))


_SR_MONTHS = {
    "januar": 1, "jan": 1, "februar": 2, "feb": 2, "mart": 3, "april": 4, "apr": 4,
    "maj": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7, "avgust": 8, "august": 8,
    "septembar": 9, "sept": 9, "sep": 9, "oktobar": 10, "okt": 10,
    "novembar": 11, "nov": 11, "decembar": 12, "dec": 12,
}


def _to_iso_z(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_date_to_utc(raw):
    """Prova RFC822, ISO8601, DD.MM.YYYY[.] [HH:MM], 'D mesec YYYY'. None se non riconosciuto: mai dedotto."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return _to_iso_z(dt)
    except (TypeError, ValueError):
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return _to_iso_z(dt)
    except ValueError:
        pass
    m = re.match(r"^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\.?\s*(?:u\s*)?(\d{1,2}):(\d{2})", raw)
    if m:
        d, mo, y, h, mi = m.groups()
        try:
            return _to_iso_z(datetime(int(y), int(mo), int(d), int(h), int(mi)))
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\.?$", raw)
    if m:
        d, mo, y = m.groups()
        try:
            return _to_iso_z(datetime(int(y), int(mo), int(d)))
        except ValueError:
            return None
    m = re.match(r"^(\d{1,2})\.?\s+([A-Za-zÀ-ſЀ-ӿ]+)\s+(\d{4})\.?", raw)
    if m:
        d, mon, y = m.groups()
        mon_key = strip_diacritics(cyr_to_lat(mon)).lower()
        month = _SR_MONTHS.get(mon_key)
        if month:
            try:
                return _to_iso_z(datetime(int(y), month, int(d)))
            except ValueError:
                return None
    return None


def sha256_hex(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- traslitterazione serba latino <-> cirillico (deterministica, tabella standard) ---

_LAT2CYR_DIGRAPHS = [
    ("Dž", "Џ"), ("DŽ", "Џ"), ("dž", "џ"),
    ("Lj", "Љ"), ("LJ", "Љ"), ("lj", "љ"),
    ("Nj", "Њ"), ("NJ", "Њ"), ("nj", "њ"),
]
_LAT2CYR_SINGLE = {
    "A": "А", "a": "а", "B": "Б", "b": "б", "V": "В", "v": "в", "G": "Г", "g": "г",
    "D": "Д", "d": "д", "Đ": "Ђ", "đ": "ђ", "E": "Е", "e": "е", "Ž": "Ж", "ž": "ж",
    "Z": "З", "z": "з", "I": "И", "i": "и", "J": "Ј", "j": "ј", "K": "К", "k": "к",
    "L": "Л", "l": "л", "M": "М", "m": "м", "N": "Н", "n": "н", "O": "О", "o": "о",
    "P": "П", "p": "п", "R": "Р", "r": "р", "S": "С", "s": "с", "T": "Т", "t": "т",
    "Ć": "Ћ", "ć": "ћ", "U": "У", "u": "у", "F": "Ф", "f": "ф", "H": "Х", "h": "х",
    "C": "Ц", "c": "ц", "Č": "Ч", "č": "ч", "Š": "Ш", "š": "ш",
}
_CYR2LAT_SINGLE = {cyr: lat for lat, cyr in _LAT2CYR_SINGLE.items()}
_CYR2LAT_SINGLE.update({"Џ": "Dž", "џ": "dž", "Љ": "Lj", "љ": "lj", "Њ": "Nj", "њ": "nj"})

_STRIP_MAP = {
    "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "dj",
    "Č": "C", "Ć": "C", "Š": "S", "Ž": "Z", "Đ": "Dj",
}


def lat_to_cyr(text):
    for lat, cyr in _LAT2CYR_DIGRAPHS:
        text = text.replace(lat, cyr)
    return "".join(_LAT2CYR_SINGLE.get(ch, ch) for ch in text)


def cyr_to_lat(text):
    return "".join(_CYR2LAT_SINGLE.get(ch, ch) for ch in text)


def strip_diacritics(text):
    return "".join(_STRIP_MAP.get(ch, ch) for ch in text)


def normalize_search(text):
    """minuscolo + senza diacritici + cirillico->latino. Solo per ricerca/matching, mai per l'output."""
    if not text:
        return ""
    return strip_diacritics(cyr_to_lat(text)).lower()


# §2a: stopword serbe molto comuni, per il SOLO confronto dedup/clustering (title_norm/text_norm).
# Deliberatamente NON dentro normalize_search: quella serve anche al matching entita' (score.py),
# dove parole come 'je'/'u'/'na' non vanno toccate. Forma normalizzata (senza diacritici, latino).
_STOPWORDS_SR = {
    "je", "su", "u", "na", "za", "od", "do", "sa", "se", "i", "a", "ali", "da", "ne",
    "koji", "koja", "koje", "kao", "ili", "to", "ce", "će", "kako", "sto", "što", "iz",
    "po", "o", "ka", "kod", "pri", "bez", "posle", "poslije", "pred", "nad", "pod",
}


def normalize_compare(text):
    """§2a — text_norm/title_norm per dedup/clustering: normalize_search + punteggiatura via +
    stopword serbe via. Mai per l'output, mai per il matching entita' (quello resta normalize_search)."""
    norm = normalize_search(text)
    no_punct = re.sub(r"[^\w\s]", " ", norm)
    words = [w for w in no_punct.split() if w not in _STOPWORDS_SR]
    return " ".join(words)


def has_cyrillic(text):
    return bool(re.search(r"[Ѐ-ӿ]", text or ""))
