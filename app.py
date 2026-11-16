"""
Engineering document assistant, a Streamlit app powered by Claude.

Upload a datasheet, manual or technical report and either summarize it, ask questions about
it, or pull its specifications into a table. The Claude calls live in src/analyzer.py so
they can be unit tested without the network.

Run locally:
    pip install -r requirements.txt
    set ANTHROPIC_API_KEY=...        (Windows)  /  export ANTHROPIC_API_KEY=...  (mac, linux)
    streamlit run app.py
"""
import os

import pandas as pd
import streamlit as st

from src import analyzer
from src.pdf_utils import read_document

st.set_page_config(page_title="Engineering Doc Assistant", page_icon="book", layout="wide")

MODEL = os.environ.get("ANTHROPIC_MODEL", analyzer.DEFAULT_MODEL)


def build_client(api_key):
    """Build an Anthropic client for the given key, or None when there is no key."""
    if not api_key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=api_key)


st.title("Engineering document assistant")
st.caption(
    "Summarize a datasheet, ask questions about a manual, or pull specifications out of a "
    "technical report. Built on the Claude API. Your document is sent to the Anthropic API "
    "for analysis and is not stored by this app."
)

with st.sidebar:
    st.subheader("Anthropic API key")
    key_input = st.text_input(
        "Your API key",
        type="password",
        help="Used only for this session to call the API, never stored. Get one at "
             "console.anthropic.com.",
    )
    st.subheader("Document")
    uploaded = st.file_uploader("Upload a PDF or text file", type=["pdf", "txt", "md"])
    pasted = st.text_area("Or paste text", height=200, placeholder="Paste a datasheet here...")
    st.caption(f"Model: `{MODEL}`")

api_key = key_input.strip() or os.environ.get("ANTHROPIC_API_KEY", "")
client = build_client(api_key)

if client is None:
    st.info(
        "Enter your Anthropic API key in the sidebar to use the app. The key is used only to "
        "make calls for your own session and is not stored. Get one at console.anthropic.com."
    )

document = ""
if uploaded is not None:
    document = read_document(uploaded.name, uploaded.getvalue())
    if not document:
        st.sidebar.error("Could not read text from that file. A scanned PDF has no text layer.")
elif pasted.strip():
    document = pasted.strip()

if document:
    st.sidebar.success(f"Loaded {len(document):,} characters")

tab_summary, tab_ask, tab_extract = st.tabs(["Summary", "Ask a question", "Extract specs"])


def guard():
    if client is None:
        st.error("Enter your Anthropic API key in the sidebar first.")
        return False
    if not document:
        st.info("Add a document in the sidebar to begin.")
        return False
    return True


with tab_summary:
    if st.button("Summarize", type="primary"):
        if guard():
            with st.spinner("Reading the document..."):
                st.markdown(analyzer.summarize(client, document, MODEL))

with tab_ask:
    question = st.text_input("Your question", placeholder="What is the rated output power?")
    if st.button("Ask"):
        if guard() and question.strip():
            with st.spinner("Looking it up..."):
                st.markdown(analyzer.answer_question(client, document, question, MODEL))

with tab_extract:
    if st.button("Extract specifications"):
        if guard():
            with st.spinner("Pulling out the specs..."):
                specs = analyzer.extract_specs(client, document, MODEL)
            if specs:
                df = pd.DataFrame([s.__dict__ for s in specs])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("Download as CSV", df.to_csv(index=False),
                                   "specifications.csv", "text/csv")
            else:
                st.info("No clear specifications found in this document.")
