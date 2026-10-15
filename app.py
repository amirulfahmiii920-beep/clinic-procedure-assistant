"""Gradio interface for the clinic procedure assistant.

Run:  .venv\\Scripts\\python app.py      then open http://127.0.0.1:7860
"""
import html
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from answer import Answer, answer  # noqa: E402
from config import CHAT_MODEL, EMBED_MODEL, INDEX_PATH  # noqa: E402
from ingest import build_index  # noqa: E402

STATUS = {
    "ANSWERED": ("ok", "Answered from the SOPs"),
    "TOOL": ("ok", "Checked against the opening hours (Python clock)"),
    "NOT_FOUND": ("warn", "Not covered by the SOPs"),
    "REFUSED_MEDICAL": ("warn", "Outside scope: medical advice"),
    "UNVERIFIED": ("bad", "Needs review: the citation check failed"),
    "MODEL_UNAVAILABLE": ("bad", "Model unavailable"),
}

EXAMPLES = [
    "What documents do I need to bring to register?",
    "What time does the clinic close on Friday?",
    "I came 20 minutes after my appointment time. Will the doctor still see me?",
    "Do senior citizens need to pay?",
    "Is the clinic open now?",
    "Is there paid parking at the clinic?",
    "What medicine should I take for a fever?",
]

CSS = """
.status{display:inline-block;padding:4px 10px;border-radius:999px;font-size:.85rem;font-weight:600;border:1px solid}
.status.ok{color:#17803d;border-color:#17803d;background:#e5f5ea}
.status.warn{color:#9a6700;border-color:#9a6700;background:#fff4d6}
.status.bad{color:#b42318;border-color:#b42318;background:#fdecea}
.src{border:1px solid var(--border-color-primary);border-radius:10px;padding:10px 12px;margin:8px 0}
.src.used{border-left:4px solid #17803d}
.src .meta{font-size:.8rem;opacity:.75}
.src pre{white-space:pre-wrap;font-size:.85rem;margin:6px 0 0}
.query{font-size:.8rem;opacity:.75;margin-top:6px}
"""


def render_panel(a: Answer) -> str:
    kind, label = STATUS[a.status]
    parts = [f'<span class="status {kind}">{label}</span>']
    if a.query:
        parts.append(f'<div class="query">Searched for: “{html.escape(a.query)}”</div>')
    if not a.sources:
        note = {"REFUSED_MEDICAL": "No SOP search is run for medical questions.",
                "TOOL": "Answered from SOP-02 opening hours by a Python function, not by the model.",
                "NOT_FOUND": "No SOP section scored above the relevance cutoff."}.get(a.status, "")
        if note:
            parts.append(f"<p>{note}</p>")
        return "\n".join(parts)
    parts.append("<h4>Evidence given to the model</h4>")
    for s in a.sources:
        used = s.n in a.cited
        tag = "Cited in the answer" if used else "Retrieved, not cited"
        parts.append(
            f'<div class="src{" used" if used else ""}">'
            f"<strong>[{s.n}] {s.doc_id}, Section {s.section}: {html.escape(s.section_title)}</strong>"
            f'<div class="meta">{tag} · {html.escape(s.doc_title)} v{s.version} · similarity {s.score:.3f}</div>'
            f"<details><summary>Show passage</summary><pre>{html.escape(s.text)}</pre></details></div>")
    return "\n".join(parts)


def format_reply(a: Answer) -> str:
    if a.status in ("ANSWERED", "UNVERIFIED") and a.cited:
        refs = ", ".join(f"{s.doc_id} §{s.section}" for s in a.sources if s.n in a.cited)
        return f"{a.text}\n\n*Source: {refs}*"
    return a.text


def respond(message: str, history: list[dict]):
    message = (message or "").strip()
    if not message:
        return history, gr.update(), ""
    prior = [{"role": m["role"], "content": m["content"]} for m in history
             if m["role"] in ("user", "assistant") and isinstance(m["content"], str)]
    a = answer(message, prior)
    history = history + [{"role": "user", "content": message},
                         {"role": "assistant", "content": format_reply(a)}]
    return history, render_panel(a), ""


def rebuild():
    info = build_index()
    return f"Index rebuilt: {info['documents']} documents, {info['chunks']} sections, {info['dimensions']}-dim vectors."


if not INDEX_PATH.exists():
    print(build_index())

with gr.Blocks(title="Clinic Procedure Assistant", css=CSS, theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# Clinic Procedure Assistant\n"
        "Answers from the clinic's own SOPs, and says so when it can't. "
        "*Klinik Kesihatan Taman Mawar is fictional; this is a training project, not medical advice.*")
    with gr.Row():
        with gr.Column(scale=3):
            chat = gr.Chatbot(type="messages", height=480, label="Conversation")
            box = gr.Textbox(placeholder="Ask about registration, opening hours, fees or appointments",
                             show_label=False, autofocus=True)
            with gr.Row():
                send = gr.Button("Ask", variant="primary")
                clear = gr.Button("New conversation")
            gr.Examples(EXAMPLES, inputs=box, label="Try a question")
        with gr.Column(scale=2):
            panel = gr.HTML('<p>Ask a question to see which SOP sections the answer is based on.</p>',
                            label="Sources")
            with gr.Accordion("System", open=False):
                gr.Markdown(f"Chat model: `{CHAT_MODEL}` · Embeddings: `{EMBED_MODEL}` · Runs locally with Ollama")
                rebuild_btn = gr.Button("Rebuild SOP index")
                rebuild_out = gr.Markdown()

    send.click(respond, [box, chat], [chat, panel, box])
    box.submit(respond, [box, chat], [chat, panel, box])
    clear.click(lambda: ([], "<p>New conversation started.</p>", ""), None, [chat, panel, box])
    rebuild_btn.click(rebuild, None, rebuild_out)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
