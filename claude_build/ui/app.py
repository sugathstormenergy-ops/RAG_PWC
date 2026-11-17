#!/usr/bin/env python3
"""
Task 8 — Simple UI (optional).

    streamlit run ui/app.py

Runs on 127.0.0.1 only (see .streamlit/config.toml in this folder and the
run command below). Logs every question with time, sources, and model name
to logs/qa_log.jsonl (same log used by ask.py), so answers can be traced
later.
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from ask import ask
from search_index import HybridIndex
from ollama_client import DEFAULT_CHAT_MODEL, ping

st.set_page_config(page_title="Engineering Docs Assistant", page_icon="📘")
st.title("📘 Offline Engineering-Docs Assistant")
st.caption(
    "Answers only from the ingested documents. Always check the page "
    "citation against the source document before relying on an answer."
)

if not ping():
    st.error(
        "Ollama is not reachable at the configured OLLAMA_HOST. "
        "Start it with `ollama serve` and make sure the chat/embedding "
        "models are pulled, then reload this page."
    )

@st.cache_resource
def get_index():
    return HybridIndex()

index = get_index()

model = st.sidebar.text_input("Chat model", value=DEFAULT_CHAT_MODEL)
top_k = st.sidebar.slider("Chunks to retrieve", 1, 10, 5)
st.sidebar.markdown("---")
st.sidebar.markdown(
    "**What this tool cannot do**\n"
    "- It cannot answer from knowledge outside the ingested documents.\n"
    "- It cannot guarantee it picked the newest revision if documents "
    "don't clearly label revisions.\n"
    "- It is not a substitute for reading the cited source page yourself "
    "on anything safety-critical."
)

question = st.text_input("Ask a question about the ingested documents:")

if st.button("Ask") and question.strip():
    with st.spinner("Searching documents and asking the model..."):
        answer, hits = ask(question, index=index, chat_model=model, top_k=top_k)
    st.markdown("### Answer")
    st.write(answer)

    with st.expander("Sources considered"):
        for h in hits:
            st.write(f"- **{h['file']}**, p.{h['page']}" + (f", sec.{h['section']}" if h.get("section") else "")
                      + (f"  _(marking: {h['marking']})_" if h.get("marking") else ""))
            st.caption(h["text"][:300] + ("..." if len(h["text"]) > 300 else ""))

st.markdown("---")
st.caption("Every question is logged with timestamp, model, and sources to logs/qa_log.jsonl.")
