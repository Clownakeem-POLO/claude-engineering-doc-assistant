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


@st.cache_resource
def get_client():
    """Build the Anthropic client once. Returns None if the key is missing."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    import anthropic
    return anthropic.Anthropic()


client = get_client()

st.title("Engineering document assistant")
st.caption(
    "Summarize a datasheet, ask questions about a manual, or pull specifications out of a "
    "technical report. Built on the Claude API. Your document is sent to the Anthropic API "
    "for analysis and is not stored by this app."
)

if client is None:
    st.warning(
        "No ANTHROPIC_API_KEY found. Set it in your environment (or in the app's secrets on "
        "Streamlit Cloud) and reload. The app does the rest."
    )

with st.sidebar:
    st.subheader("Document")
    uploaded = st.file_uploader("Upload a PDF or text file", type=["pdf", "txt", "md"])
    pasted = st.text_area("Or paste text", height=200, placeholder="Paste a datasheet here...")
    st.caption(f"Model: `{MODEL}`")

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
        st.error("Set ANTHROPIC_API_KEY first.")
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
