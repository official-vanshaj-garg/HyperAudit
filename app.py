from pathlib import Path
import tempfile

import streamlit as st

from src.config import DATA_DIR
from src.parser import parse_documents

st.set_page_config(page_title="HyperAudit", layout="wide")

st.title("HyperAudit")
st.caption("Phase 2: PDF page-wise text extraction")

st.subheader("Option 1: Use local data file")
default_pdf = DATA_DIR / "gauntlet.pdf"

if st.button("Parse data/gauntlet.pdf"):
    if not default_pdf.exists():
        st.error(f"File not found: {default_pdf}")
    else:
        with st.spinner("Parsing PDF..."):
            parsed = parse_documents(default_pdf)

        st.success(f"Parsed {parsed['total_pages']} pages from {parsed['file_name']}")

        for page in parsed["pages"][:5]:
            with st.expander(f"Page {page['page_number']} | chars: {page['char_count']}"):
                st.text(page["text"][:4000] or "[NO TEXT FOUND]")


st.divider()

st.subheader("Option 2: Upload a PDF")
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.read())
        temp_pdf_path = Path(tmp_file.name)

    with st.spinner("Parsing uploaded PDF..."):
        parsed = parse_documents(temp_pdf_path)

    st.success(f"Parsed {parsed['total_pages']} pages from {uploaded_file.name}")

    for page in parsed["pages"][:5]:
        with st.expander(f"Page {page['page_number']} | chars: {page['char_count']}"):
            st.text(page["text"][:4000] or "[NO TEXT FOUND]")