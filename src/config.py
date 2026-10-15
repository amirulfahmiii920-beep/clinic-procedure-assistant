"""Shared settings for the clinic procedure assistant."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOP_DIR = ROOT / "data" / "sop"
INDEX_PATH = ROOT / "data" / "index.sqlite"

OLLAMA_URL = "http://localhost:11434"
EMBED_MODEL = "embeddinggemma"
# Override with the CHAT_MODEL environment variable, e.g. to compare model sizes.
# qwen2.5:3b was chosen over 1.5b after the comparison in tests/manual_review.md.
CHAT_MODEL = os.environ.get("CHAT_MODEL", "qwen2.5:3b")
TIMEOUT_S = 120

# embeddinggemma was trained with task prefixes; using them improves retrieval.
QUERY_PREFIX = "task: search result | query: "
DOC_PREFIX = "title: {title} | text: "

TOP_K = 3
# Below this cosine score a chunk is not treated as evidence.
# Calibrated with tests/questions.csv (see tests/retrieval_results.md).
MIN_SCORE = 0.45
