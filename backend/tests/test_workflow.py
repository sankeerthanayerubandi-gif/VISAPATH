"""
End-to-end and safety-boundary tests.
Tests that need a live LLM call are marked and skipped automatically if
OPENAI_API_KEY is not set, so `pytest` still runs cleanly for a beginner
who hasn't configured an API key yet.
"""
import os
import pytest

from backend.src.schemas.audit_schema import AuditReport, RequirementResult
from backend.src.agents.workflow import _enforce_output_safety, scan_documents_for_security
from backend.src.schemas.audit_schema import ExtractedDocument
from backend.src.ingestion.document_loader import extract_document
from backend.config.settings import TEST_DOCUMENTS_DIR

requires_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"), reason="OPENAI_API_KEY not set; skipping live LLM test"
)


def test_document_extraction_end_to_end():
    path = os.path.join(TEST_DOCUMENTS_DIR, "passport.txt")
    docs = extract_document(path)
    assert len(docs) == 1
    assert "KUMAR" in docs[0].text
    assert docs[0].is_suspicious is False


def test_manipulated_document_flagged_but_not_deleted():
    path = os.path.join(TEST_DOCUMENTS_DIR, "manipulated.txt")
    docs = extract_document(path)
    assert docs[0].is_suspicious is True
    # Content must be preserved as evidence, never stripped.
    assert "IGNORE ALL PREVIOUS INSTRUCTIONS" in docs[0].text


def test_security_scan_across_documents():
    path = os.path.join(TEST_DOCUMENTS_DIR, "manipulated.txt")
    docs = extract_document(path)
    findings = scan_documents_for_security(docs)
    assert len(findings) >= 1
    assert findings[0].filename == "manipulated.txt"


def test_safety_enforcement_blocks_forbidden_phrase():
    bad_report = AuditReport(
        visa_category="B-1/B-2",
        requirements=[
            RequirementResult(
                requirement="Valid passport",
                status="satisfied",
                evidence="applicant is guaranteed visa approval",
                source="passport.txt",
            )
        ],
        confidence=0.9,
    )
    with pytest.raises(ValueError):
        _enforce_output_safety(bad_report)


def test_safety_enforcement_passes_clean_report():
    good_report = AuditReport(
        visa_category="B-1/B-2",
        requirements=[
            RequirementResult(
                requirement="Valid passport",
                status="satisfied",
                evidence="Passport number N1234567 found in passport.txt",
                source="passport.txt",
            )
        ],
        confidence=0.9,
    )
    result = _enforce_output_safety(good_report)
    assert result.advisory_only is True
    assert "does not determine immigration eligibility" in result.disclaimer


@requires_api_key
def test_checklist_agent_live_call_returns_structured_results():
    from backend.src.agents.checklist_agent import run_checklist_agent

    docs = extract_document(os.path.join(TEST_DOCUMENTS_DIR, "passport.txt"))
    context = "Requirement: A valid passport is required. [SOURCE: sample_requirements.txt]"
    results = run_checklist_agent("B-1/B-2", context, docs)
    assert isinstance(results, list)


@requires_api_key
def test_consistency_agent_detects_dob_mismatch_live():
    from backend.src.agents.consistency_agent import run_consistency_agent

    docs = extract_document(os.path.join(TEST_DOCUMENTS_DIR, "passport.txt"))
    docs += extract_document(os.path.join(TEST_DOCUMENTS_DIR, "ds160.txt"))
    inconsistencies = run_consistency_agent(docs)
    fields = [i.field.lower() for i in inconsistencies]
    assert any("birth" in f for f in fields)
