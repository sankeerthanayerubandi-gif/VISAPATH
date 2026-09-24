"""
Top-level orchestration: ties together security scanning, RAG retrieval,
the checklist agent, the consistency agent, and the judge — producing
the final AuditReport + JudgeEvaluation pair the Streamlit app displays.
"""
from typing import List, Tuple
import logging

from backend.src.schemas.audit_schema import (
    AuditReport,
    JudgeEvaluation,
    SecurityFinding,
    ExtractedDocument,
)
from backend.src.security.injection_defense import scan_text
from backend.src.rag.retriever import get_relevant_requirements, format_context
from backend.src.agents.checklist_agent import run_checklist_agent
from backend.src.agents.consistency_agent import run_consistency_agent
from backend.src.agents.judge_agent import run_judge_agent
from backend.config.settings import DISCLAIMER, FORBIDDEN_OUTPUT_PHRASES

logger = logging.getLogger("visapath")


def scan_documents_for_security(documents: List[ExtractedDocument]) -> List[SecurityFinding]:
    findings = []
    for doc in documents:
        is_suspicious, matches = scan_text(doc.text)
        if is_suspicious:
            for snippet in matches:
                findings.append(
                    SecurityFinding(filename=doc.filename, flagged_text=snippet, reason="Prompt-injection pattern detected")
                )
    return findings


def _enforce_output_safety(report: AuditReport) -> AuditReport:
    """Belt-and-suspenders check: strip/flag any forbidden phrase that
    somehow made it into a free-text field."""
    text_fields = []
    for r in report.requirements:
        text_fields.append(r.evidence)
    combined = " ".join(text_fields).lower()
    for phrase in FORBIDDEN_OUTPUT_PHRASES:
        if phrase in combined:
            logger.error("Forbidden phrase detected in output: %s", phrase)
            raise ValueError(
                "Safety violation: generated content contained a forbidden "
                f"eligibility/approval phrase ('{phrase}'). Output blocked."
            )
    report.disclaimer = DISCLAIMER
    report.advisory_only = True
    return report


def run_full_audit(
    visa_category: str,
    documents: List[ExtractedDocument],
    vectordb,
    required_document_names: List[str],
) -> Tuple[AuditReport, JudgeEvaluation, List[SecurityFinding]]:
    logger.info("Audit started for visa_category=%s", visa_category)

    # 1. Security scan (never blocks — flags only)
    security_findings = scan_documents_for_security(documents)

    # 2. Retrieve requirement context from the vector DB
    logger.info("Retrieval started")
    retrieved = get_relevant_requirements(
        vectordb, visa_category, query=f"required documents for {visa_category} visa"
    )
    requirement_context = format_context(retrieved)

    # 3. Checklist agent
    requirement_results = run_checklist_agent(visa_category, requirement_context, documents)

    # 4. Consistency agent
    inconsistencies = run_consistency_agent(documents)

    # 5. Determine present vs missing documents (simple filename-based check,
    #    the checklist agent's per-requirement status is the authoritative signal)
    uploaded_names = sorted({d.filename for d in documents})
    missing = [name for name in required_document_names if name not in uploaded_names]

    confidence = 0.5
    if requirement_results:
        satisfied = sum(1 for r in requirement_results if r.status == "satisfied")
        confidence = round(satisfied / len(requirement_results), 2)

    report = AuditReport(
        visa_category=visa_category,
        documents_present=uploaded_names,
        documents_missing=missing,
        requirements=requirement_results,
        inconsistencies_flagged=inconsistencies,
        security_findings=security_findings,
        confidence=confidence,
    )
    report = _enforce_output_safety(report)
    logger.info("Audit completed")

    # 6. Judge evaluation
    document_summary = "\n".join(f"{d.filename}: {d.text[:200]}" for d in documents)
    judge_result = run_judge_agent(report, requirement_context, document_summary)
    logger.info("Judge completed")

    return report, judge_result, security_findings
