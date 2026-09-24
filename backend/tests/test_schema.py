import pytest
from pydantic import ValidationError
from backend.src.schemas.audit_schema import (
    AuditReport,
    RequirementResult,
    Inconsistency,
    JudgeEvaluation,
)


def test_requirement_result_valid_status():
    r = RequirementResult(requirement="Valid passport", status="satisfied", evidence="Found passport number", source="passport.txt")
    assert r.status == "satisfied"


def test_requirement_result_invalid_status_rejected():
    with pytest.raises(ValidationError):
        RequirementResult(requirement="Valid passport", status="approved", evidence="", source="")


def test_inconsistency_requires_fields():
    inc = Inconsistency(
        field="Date of Birth",
        documents=["passport.txt", "ds160.txt"],
        description="Date of birth differs between documents.",
        severity="high",
        evidence="10 JAN 2002 vs 11 JAN 2002",
    )
    assert inc.severity == "high"


def test_audit_report_confidence_bounds():
    with pytest.raises(ValidationError):
        AuditReport(visa_category="B-1/B-2", confidence=1.5)


def test_audit_report_defaults_advisory_only_true():
    report = AuditReport(visa_category="B-1/B-2", confidence=0.8)
    assert report.advisory_only is True
    assert "does not determine immigration eligibility" in report.disclaimer


def test_judge_evaluation_score_bounds():
    with pytest.raises(ValidationError):
        JudgeEvaluation(
            checklist_accuracy=1.1,
            evidence_grounding=0.5,
            consistency_accuracy=0.5,
            safety_score=0.5,
            overall_score=0.5,
        )
