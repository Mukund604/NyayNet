"""Tests for evidence compiler."""

import pytest

from nyaynet.common.utils import generate_id, utc_now_iso, compute_sha256
from nyaynet.evidence.evidence_compiler import EvidenceCompiler


@pytest.fixture
def compiler(comment_repo, classification_repo, severity_repo, decision_repo, evidence_repo, audit_logger):
    return EvidenceCompiler(
        comment_repo, classification_repo, severity_repo,
        decision_repo, evidence_repo, audit_logger,
    )


def _insert_comment(repo, comment_id, username, text):
    timestamp = utc_now_iso()
    repo.insert({
        "id": comment_id,
        "instagram_comment_id": f"ig_{comment_id}",
        "instagram_post_id": "post_1",
        "username": username,
        "text": text,
        "timestamp": timestamp,
        "source": "mock",
        "raw_data": {},
        "checksum": compute_sha256(f"{username}|{text}|{timestamp}"),
    })


def _insert_classification(repo, comment_id, is_hateful=True, labels=None):
    cls_id = generate_id()
    repo.insert({
        "id": cls_id,
        "comment_id": comment_id,
        "method": "hybrid",
        "labels": labels or ["abuse"],
        "confidence_scores": {"abuse": 0.9},
        "overall_confidence": 0.9,
        "is_hateful": is_hateful,
    })
    return cls_id


def test_compile_evidence(compiler, comment_repo, classification_repo, decision_repo):
    username = "bad_user"

    # Insert offensive comments
    for i in range(3):
        cid = f"comment_{i}"
        _insert_comment(comment_repo, cid, username, f"Offensive text {i}")
        _insert_classification(classification_repo, cid)

    # Insert a decision
    decision_id = generate_id()
    decision_repo.insert({
        "id": decision_id,
        "comment_id": "comment_0",
        "username": username,
        "action": "recommend_complaint",
        "confidence": 0.9,
        "reasoning": "Multiple offenses",
        "requires_human_approval": True,
    })

    # Compile evidence
    package = compiler.compile(decision_id)
    assert package.username == username
    assert len(package.comment_ids) == 3
    assert package.complaint_text is not None
    assert "bad_user" in package.complaint_text
    assert len(package.legal_sections) > 0


def test_compile_generates_complaint_text(compiler, comment_repo, classification_repo, decision_repo):
    username = "harasser"
    _insert_comment(comment_repo, "c1", username, "Threatening message")
    _insert_classification(classification_repo, "c1", labels=["threat"])

    decision_id = generate_id()
    decision_repo.insert({
        "id": decision_id,
        "comment_id": "c1",
        "username": username,
        "action": "recommend_complaint",
        "confidence": 0.9,
        "reasoning": "Threat detected",
        "requires_human_approval": True,
    })

    package = compiler.compile(decision_id)
    assert "COMPLAINT" in package.complaint_text
    assert "harasser" in package.complaint_text


def test_compile_nonexistent_decision(compiler):
    with pytest.raises(ValueError):
        compiler.compile("nonexistent_id")
