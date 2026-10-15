"""Split the SOP files into section chunks, embed them and store them in SQLite.

Each SOP section (a "## n. Heading" block) becomes one chunk. Sections are short and
self-contained, so splitting on them keeps every rule whole and gives each chunk an
exact citation (document + section) without needing word-window overlap.

Run:  python src/ingest.py
"""
import json
import re
import sqlite3
from pathlib import Path

from config import DOC_PREFIX, EMBED_MODEL, INDEX_PATH, SOP_DIR
from ollama_client import embed

HEADING = re.compile(r"^## (\d+)\.\s+(.+)$", re.M)


def parse_sop(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    title_line = text.splitlines()[0].lstrip("# ").strip()          # "SOP-01: Patient Registration"
    doc_id, title = [s.strip() for s in title_line.split(":", 1)]
    version = re.search(r"version ([\d.]+)", text)
    matches = list(HEADING.finditer(text))
    chunks = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        chunks.append({
            "id": f"{doc_id}#s{m.group(1)}",
            "doc_id": doc_id,
            "doc_title": title,
            "section": m.group(1),
            "section_title": m.group(2).strip(),
            "version": version.group(1) if version else "",
            "file": path.name,
            "text": f"{m.group(2).strip()}\n{body}",
        })
    return chunks


def build_index(db_path: Path = INDEX_PATH) -> dict:
    chunks = [c for p in sorted(SOP_DIR.glob("*.md")) for c in parse_sop(p)]
    if not chunks:
        raise SystemExit(f"No SOP files found in {SOP_DIR}")
    inputs = [DOC_PREFIX.format(title=f"{c['doc_title']} - {c['section_title']}") + c["text"] for c in chunks]
    vectors = embed(inputs, EMBED_MODEL)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as con:
        con.execute("DROP TABLE IF EXISTS chunks")
        con.execute("DROP TABLE IF EXISTS meta")
        con.execute("""CREATE TABLE chunks (id TEXT PRIMARY KEY, doc_id TEXT, doc_title TEXT,
                       section TEXT, section_title TEXT, version TEXT, file TEXT,
                       text TEXT, vector TEXT)""")
        con.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        con.executemany(
            "INSERT INTO chunks VALUES (?,?,?,?,?,?,?,?,?)",
            [(c["id"], c["doc_id"], c["doc_title"], c["section"], c["section_title"],
              c["version"], c["file"], c["text"], json.dumps(v)) for c, v in zip(chunks, vectors)],
        )
        # Record which embedding model built the index, so a model change forces a rebuild.
        con.execute("INSERT INTO meta VALUES ('embed_model', ?)", (EMBED_MODEL,))
    return {"documents": len({c["doc_id"] for c in chunks}), "chunks": len(chunks),
            "dimensions": len(vectors[0]), "embed_model": EMBED_MODEL}


if __name__ == "__main__":
    print(build_index())
