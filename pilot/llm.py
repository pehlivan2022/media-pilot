"""llm(prompt) -> str | None. urllib.request, niente SDK. Provider da env o esplicito; nessuna chiave -> None.

Endpoint/formato verificati sulla documentazione ufficiale corrente (platform.claude.com,
api-docs.deepseek.com) il giorno della scrittura di questo file, non ricordati a memoria.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ANTHROPIC_MODEL = "claude-sonnet-5"
DEEPSEEK_MODEL = "deepseek-v4-pro"

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv():
    """Popola os.environ da .env (KEY=VALUE per riga) solo per le chiavi non gia' presenti.
    Mai stampato, mai loggato. Nessuna dipendenza: e' il file che l'utente non committa."""
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip()


_load_dotenv()


def llm(prompt, max_tokens=800, provider=None, timeout=90, caller=None):
    if provider is None:
        provider = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "deepseek" if os.environ.get("DEEPSEEK_API_KEY") else None
    if provider not in ("anthropic", "deepseek"):
        return None
    if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    if provider == "deepseek" and not os.environ.get("DEEPSEEK_API_KEY"):
        return None

    from pilot import spend
    spend.check_cap()  # fuori dal try sotto: deve propagare, non degradare a None
    if caller is None:
        caller = sys._getframe(1).f_globals.get("__name__", "unknown")

    try:
        if provider == "anthropic":
            body = json.dumps({
                "model": ANTHROPIC_MODEL, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages", data=body,
                headers={
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            usage = data.get("usage") or {}
            spend.record("anthropic", ANTHROPIC_MODEL, usage.get("input_tokens", 0),
                         usage.get("output_tokens", 0), caller)
            return data["content"][0]["text"]
        else:
            body = json.dumps({
                "model": DEEPSEEK_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.deepseek.com/chat/completions", data=body,
                headers={
                    "Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            usage = data.get("usage") or {}
            spend.record("deepseek", DEEPSEEK_MODEL, usage.get("prompt_tokens", 0),
                         usage.get("completion_tokens", 0), caller)
            return data["choices"][0]["message"]["content"]
    except Exception:
        # qualunque fallimento di rete/formato degrada a None: la pipeline continua senza LLM
        return None
