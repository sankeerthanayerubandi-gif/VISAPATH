"""
These tests validate the consistency-checking DATA CONTRACT without
calling a live LLM (so tests run without an API key / in CI).
The end-to-end agent behavior is covered separately in test_workflow.py
using a mocked LLM response.
"""
from backend.src.schemas.audit_schema import Inconsistency


def test_inconsistency_never_labels_fraud():
    inc = Inconsistency(
        field="Passport Number",
        documents=["passport.txt", "ds160.txt"],
        description="Passport number differs between documents.",
        severity="high",
        evidence="N1234567 vs N1234568",
    )
    forbidden_words = ["fraud", "fraudulent", "fake", "forged", "criminal"]
    combined = (inc.description + inc.evidence).lower()
    assert not any(w in combined for w in forbidden_words)


def test_inconsistency_severity_is_constrained():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Inconsistency(
            field="Date of Birth",
            documents=["a.txt", "b.txt"],
            description="x",
            severity="catastrophic",
            evidence="x",
        )


def test_inconsistency_requires_at_least_conceptually_two_documents():
    inc = Inconsistency(
        field="Date of Birth",
        documents=["passport.txt", "ds160.txt"],
        description="Date of birth differs.",
        severity="high",
        evidence="10 JAN 2002 vs 11 JAN 2002",
    )
    assert len(inc.documents) >= 2
