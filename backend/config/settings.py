"""
Central configuration for VisaPath.
Loads settings from environment variables (via .env) so no secrets
are ever hard-coded in source files.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- LLM / Embeddings ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5-mini" if "api.manus.im" in OPENAI_API_BASE else "gpt-4o-mini",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Auditing must be deterministic, not creative.
LLM_TEMPERATURE = 0

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS_DIR = os.path.join(BASE_DIR, "data", "requirements")
TEST_DOCUMENTS_DIR = os.path.join(BASE_DIR, "data", "test_documents")
EVALUATION_DIR = os.path.join(BASE_DIR, "data", "evaluation")
VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")

# --- RAG tuning ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
RETRIEVAL_K = 4

# --- Visa categories currently supported ---
SUPPORTED_VISA_CATEGORIES = ["B-1/B-2", "F-1", "Immigrant"]

# --- Safety disclaimer shown everywhere in the app and every report ---
DISCLAIMER = (
    "This system performs document completeness and consistency checks only. "
    "It does not determine immigration eligibility, predict visa approval or "
    "refusal, or provide legal advice. Results require human/paralegal review."
)

# --- Phrases that must NEVER appear in a generated report ---
FORBIDDEN_OUTPUT_PHRASES = [
    "guaranteed approval",
    "guaranteed visa approval",
    "visa will be approved",
    "eligible for visa",
    "visa approval probability",
    "will definitely be approved",
    "guarantee visa approval",
]


def validate_config():
    """Raise a clear, user-friendly error if required config is missing."""
    if not OPENAI_API_KEY:
        raise EnvironmentError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
