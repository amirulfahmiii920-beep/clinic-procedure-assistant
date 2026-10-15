"""Minimal Ollama HTTP client using only the standard library.

Token counts from every call are added to USAGE so the answer pipeline can log how many
model calls and tokens one question cost.
"""
import json
import urllib.error
import urllib.request

from config import OLLAMA_URL, TIMEOUT_S

USAGE = {"calls": 0, "tokens_in": 0, "tokens_out": 0}


def reset_usage() -> None:
    USAGE.update(calls=0, tokens_in=0, tokens_out=0)


class OllamaUnavailable(RuntimeError):
    """Raised when the local Ollama service cannot be reached."""


def _post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        OLLAMA_URL + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
            out = json.load(r)
    except urllib.error.URLError as e:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {OLLAMA_URL}. Start Ollama and try again. ({e})"
        ) from e
    USAGE["calls"] += 1
    USAGE["tokens_in"] += out.get("prompt_eval_count", 0)
    USAGE["tokens_out"] += out.get("eval_count", 0)
    return out


def embed(texts: list[str], model: str) -> list[list[float]]:
    return _post("/api/embed", {"model": model, "input": texts})["embeddings"]


def chat(messages: list[dict], model: str, temperature: float = 0.0,
         schema: dict | None = None) -> str:
    """Return the reply text. With a JSON schema, Ollama constrains the reply to match it."""
    payload = {"model": model, "messages": messages, "stream": False,
               "options": {"temperature": temperature}}
    if schema:
        payload["format"] = schema
    return _post("/api/chat", payload)["message"]["content"]
