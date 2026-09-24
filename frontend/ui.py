"""
VisaPath — Document Checklist & Application Consistency Agent
Streamlit dashboard entry point.
"""

# --- Deployment fix: must run before anything imports chromadb. ---
# Most cloud hosts (Streamlit Community Cloud, Render, Railway, etc.) ship
# a system sqlite3 older than what chromadb requires, causing:
#   RuntimeError: Your system has an unsupported version of sqlite3
# Swapping in pysqlite3-binary (a modern, self-contained build) fixes this.
# Harmless locally / on platforms with a modern sqlite3 already.
try:
    __import__("pysqlite3")
    import sys as _sys
    _sys.modules["sqlite3"] = _sys.modules.pop("pysqlite3")
except ImportError:
    pass

import os
import json
import logging
import tempfile

import streamlit as st
import pandas as pd

from backend.config.settings import (
    SUPPORTED_VISA_CATEGORIES,
    DISCLAIMER,
    validate_config,
)
from backend.src.ingestion.document_loader import extract_document
from backend.src.rag.vectorstore import build_vectorstore, load_vectorstore
from backend.src.agents.workflow import run_full_audit


@st.cache_resource(show_spinner=False)
def get_vectorstore():
    """
    Load the knowledge base, building it on first run if it isn't there.
    Most cloud hosts wipe local disk on every redeploy/restart (the same
    issue as SQLite files disappearing) — since this vector store is
    cheaply rebuilt from the small sample .txt files in data/requirements/,
    we just rebuild it automatically instead of requiring a manual click
    after every deploy. Cached per-process so it only happens once.
    """
    try:
        return load_vectorstore()
    except FileNotFoundError:
        return build_vectorstore()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visapath")

st.set_page_config(page_title="VisaPath", layout="wide")

# ---------------------------------------------------------------- SIDEBAR
st.sidebar.title("VisaPath")
visa_category = st.sidebar.selectbox("Visa category", SUPPORTED_VISA_CATEGORIES)

if st.sidebar.button("Build / refresh knowledge base"):
    try:
        with st.spinner("Embedding requirement documents into ChromaDB..."):
            build_vectorstore()
        get_vectorstore.clear()  # force the cached resource to reload
        st.sidebar.success("Knowledge base built successfully.")
    except Exception as e:
        st.sidebar.error(f"Could not build knowledge base: {e}")

with st.sidebar.expander("About / Safety Information"):
    st.write(DISCLAIMER)
    st.caption(
        "Sample requirement documents in this project are for development "
        "and testing only. Replace them with current official government "
        "sources before any real use."
    )

# ---------------------------------------------------------------- HEADER
st.title("VisaPath")
st.subheader("Document Checklist & Application Consistency Agent")
st.info(DISCLAIMER)

try:
    validate_config()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()

# ---------------------------------------------------------------- SECTION 1
st.header("1. Application Information")
required_docs_input = st.text_input(
    "Required document filenames for this application (comma-separated)",
    value="passport.txt, ds160.txt, bank_statement.txt",
    help="Used only to check which expected filenames are missing from the upload.",
)
required_document_names = [d.strip() for d in required_docs_input.split(",") if d.strip()]

# ---------------------------------------------------------------- SECTION 2
st.header("2. Upload Documents")
uploaded_files = st.file_uploader(
    "Upload PDF, DOCX, or TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True
)

run_audit = st.button("Run Audit", type="primary", disabled=not uploaded_files)

if run_audit and uploaded_files:
    all_documents = []
    with st.spinner("Extracting documents..."):
        for uf in uploaded_files:
            tmp_path = None
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix="_" + uf.name) as tmp:
                    tmp.write(uf.getbuffer())
                    tmp_path = tmp.name
                extracted = extract_document(tmp_path)
                # Restore original filename (tempfile prefixes/suffixes it)
                for doc in extracted:
                    doc.filename = uf.name
                all_documents.extend(extracted)
            except Exception as e:
                st.error(f"Failed to process '{uf.name}': {e}")
            finally:
                if tmp_path and os.path.exists(tmp_path):
                    os.remove(tmp_path)

    if not all_documents:
        st.warning("No documents were successfully extracted.")
        st.stop()

    try:
        with st.spinner("Loading knowledge base..."):
            vectordb = get_vectorstore()
    except Exception as e:
        st.error(f"Could not load or build the knowledge base: {e}")
        st.stop()

    with st.spinner("Running audit — security scan, RAG retrieval, checklist, consistency, and judge..."):
        try:
            report, judge, security_findings = run_full_audit(
                visa_category, all_documents, vectordb, required_document_names
            )
        except ValueError as e:
            st.error(f"Audit blocked by safety enforcement: {e}")
            st.stop()
        except Exception as e:
            st.error(f"Audit failed: {e}")
            st.stop()

    # ------------------------------------------------------- METRICS
    st.header("Dashboard Metrics")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documents Uploaded", len(uploaded_files))
    c2.metric("Documents Present", len(report.documents_present))
    c3.metric("Documents Missing", len(report.documents_missing))
    c4.metric("Inconsistencies Detected", len(report.inconsistencies_flagged))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Security Warnings", len(security_findings))
    c6.metric("Audit Confidence", f"{report.confidence:.2f}")
    c7.metric("Judge Score", f"{judge.overall_score:.2f}")
    c8.metric("Safety Score", f"{judge.safety_score:.2f}")

    # ------------------------------------------------------- SECTION 3
    st.header("3. Security Scan")
    if security_findings:
        st.warning(f"{len(security_findings)} suspicious pattern(s) detected in uploaded documents.")
        for f in security_findings:
            with st.expander(f"⚠️ {f.filename}"):
                st.write(f"**Reason:** {f.reason}")
                st.code(f.flagged_text)
        st.caption("Flagged content is preserved as evidence and was never followed as an instruction.")
    else:
        st.success("No prompt-injection patterns detected.")

    # ------------------------------------------------------- SECTION 4
    st.header("4. Requirement Matching")
    if report.requirements:
        df = pd.DataFrame([r.model_dump() for r in report.requirements])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No requirement results returned.")

    # ------------------------------------------------------- SECTION 5
    st.header("5. Missing Documents")
    if report.documents_missing:
        for d in report.documents_missing:
            st.error(f"Missing: {d}")
    else:
        st.success("All expected documents were uploaded.")

    # ------------------------------------------------------- SECTION 6
    st.header("6. Cross-Document Consistency")
    if report.inconsistencies_flagged:
        for inc in report.inconsistencies_flagged:
            severity_fn = {"high": st.error, "medium": st.warning, "low": st.info}[inc.severity]
            severity_fn(f"**{inc.field}** differs across {', '.join(inc.documents)}")
            with st.expander("Evidence"):
                st.write(inc.description)
                st.code(inc.evidence)
    else:
        st.success("No cross-document inconsistencies detected.")

    # ------------------------------------------------------- SECTION 7
    st.header("7. Evidence")
    for r in report.requirements:
        with st.expander(f"{r.requirement} — {r.status.upper()}"):
            st.write(f"**Evidence:** {r.evidence or 'None provided'}")
            st.write(f"**Source:** {r.source or 'N/A'}")

    # ------------------------------------------------------- SECTION 8
    st.header("8. LLM-as-a-Judge")
    jc1, jc2, jc3, jc4, jc5 = st.columns(5)
    jc1.metric("Checklist Accuracy", f"{judge.checklist_accuracy:.2f}")
    jc2.metric("Evidence Grounding", f"{judge.evidence_grounding:.2f}")
    jc3.metric("Consistency Accuracy", f"{judge.consistency_accuracy:.2f}")
    jc4.metric("Safety Score", f"{judge.safety_score:.2f}")
    jc5.metric("Overall Score", f"{judge.overall_score:.2f}")
    st.write(judge.explanation)
    if judge.errors:
        st.warning("Judge-identified issues:")
        for err in judge.errors:
            st.write(f"- {err}")

    # ------------------------------------------------------- SECTION 9
    st.header("9. Structured JSON Report")
    full_report = {
        "audit_report": report.model_dump(),
        "judge_evaluation": judge.model_dump(),
    }
    with st.expander("View full JSON"):
        st.json(full_report)

    # ------------------------------------------------------- SECTION 10
    st.header("10. Download Report")
    json_bytes = json.dumps(full_report, indent=2).encode("utf-8")
    st.download_button("Download JSON Report", data=json_bytes, file_name="visapath_report.json", mime="application/json")

    csv_rows = [r.model_dump() for r in report.requirements]
    if csv_rows:
        csv_bytes = pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8")
        st.download_button("Download Requirements CSV", data=csv_bytes, file_name="visapath_requirements.csv", mime="text/csv")

st.divider()
st.caption(DISCLAIMER)
