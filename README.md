# VisaPath — Streamlit Deployment Package

VisaPath is an evidence-first document completeness and cross-document consistency checker. It does **not** predict visa approval, determine immigration eligibility, or provide legal advice. Every result requires human or paralegal review.

## Clean structure

```text
VisaPath_deployment_ready/
├── app.py                 # Streamlit entrypoint
├── frontend/              # Streamlit UI
├── backend/               # configuration, ingestion, RAG, agents, schemas, tests, data
├── requirements.txt
├── .env.example
├── .streamlit/config.toml
├── Procfile
├── runtime.txt
└── README.md
```

The package intentionally excludes `.venv`, `node_modules`, `__pycache__`, `.pyc` files, Chroma runtime data, secrets, and temporary files.

## Run locally

Requires Python 3.11 or newer. From the extracted project directory:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY. Never commit the real .env.
streamlit run app.py
```

The app opens at the URL printed by Streamlit. Without an API key it starts safely and displays a clear configuration message rather than crashing.

## Streamlit Community Cloud

1. Upload this folder to a GitHub repository.
2. In Streamlit Community Cloud choose **New app**.
3. Set the branch and main file path to `app.py`.
4. Add `OPENAI_API_KEY`, and optionally `OPENAI_MODEL`, `OPENAI_API_BASE`, and `EMBEDDING_MODEL`, under **Advanced settings → Secrets**.
5. Deploy. The knowledge base is rebuilt automatically from `backend/data/requirements/` when the ephemeral deployment has no local vector database.

## Other Python hosts

Use `pip install -r requirements.txt` as the build command and the included `Procfile` as the start command. The process listens on `${PORT:-8501}` and binds to `0.0.0.0`, so it is compatible with Render, Railway, and similar hosts.

## Verify the package

```bash
python -m compileall -q app.py frontend backend
pytest -q
```

The tests use bundled sample documents and skip live LLM calls when `OPENAI_API_KEY` is not configured.

## Included functionality

The package preserves the original Streamlit workflow: PDF/DOCX/TXT extraction, visa-category selection, Chroma-backed requirement retrieval, prompt-injection scanning, checklist matching, cross-document consistency checks, structured Pydantic reports, LLM-as-a-Judge scoring, knowledge-base refresh, JSON download, and CSV requirement export.

> **Safety boundary:** uploaded document text is treated as untrusted evidence, never as instructions.
