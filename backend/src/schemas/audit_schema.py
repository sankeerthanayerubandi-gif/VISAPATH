"""
Pydantic models that define the ONLY shapes the LLM is allowed to return.
Using `llm.with_structured_output(Model)` means we never hand-parse JSON
strings and never let the model return free-form, unvalidated text for
the audit result.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Status = Literal["satisfied", "missing", "unclear"]
Severity = Literal["low", "medium", "high"]


class RequirementResult(BaseModel):
    requirement: str = Field(..., description="The requirement text being checked.")
    status: Status = Field(
        ...,
        description=(
            "'satisfied' only if evidence was found in the uploaded documents. "
            "'missing' if no relevant document was provided. "
            "'unclear' if evidence is ambiguous or the requirement is not "
            "present in the retrieved knowledge base — never guess."
        ),
    )
    evidence: str = Field(
        default="",
        description="Exact snippet or fact from a document that supports the status.",
    )
    source: str = Field(
        default="",
        description="Filename or official requirement document this came from.",
    )


class Inconsistency(BaseModel):
    field: str = Field(..., description="The factual field that differs, e.g. 'Date of Birth'.")
    documents: List[str] = Field(..., description="Filenames of the documents being compared.")
    description: str = Field(..., description="Neutral description of the discrepancy found.")
    severity: Severity
    evidence: str = Field(..., description="The exact conflicting values from each document.")


class SecurityFinding(BaseModel):
    filename: str
    flagged_text: str
    reason: str


class AuditReport(BaseModel):
    """The single, top-level structured object the whole app produces."""
    visa_category: str
    documents_present: List[str] = Field(default_factory=list)
    documents_missing: List[str] = Field(default_factory=list)
    requirements: List[RequirementResult] = Field(default_factory=list)
    inconsistencies_flagged: List[Inconsistency] = Field(default_factory=list)
    security_findings: List[SecurityFinding] = Field(default_factory=list)
    confidence: float = Field(..., ge=0.0, le=1.0)
    advisory_only: bool = True
    disclaimer: str = Field(
        default=(
            "This system performs document completeness and consistency checks "
            "only. It does not determine immigration eligibility, predict visa "
            "approval or refusal, or provide legal advice. Results require "
            "human/paralegal review."
        )
    )


class JudgeEvaluation(BaseModel):
    checklist_accuracy: float = Field(..., ge=0.0, le=1.0)
    evidence_grounding: float = Field(..., ge=0.0, le=1.0)
    consistency_accuracy: float = Field(..., ge=0.0, le=1.0)
    safety_score: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    errors: List[str] = Field(default_factory=list)
    explanation: str = ""


class ExtractedDocument(BaseModel):
    """Metadata-preserving container for one uploaded file's text."""
    filename: str
    document_type: str
    source: str = "user_upload"
    page: Optional[int] = None
    text: str
    is_suspicious: bool = False
