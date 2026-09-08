from pr_review_agent.formatting import (
    choose_event,
    format_comment_body,
    format_findings_as_text,
    format_summary,
)
from pr_review_agent.reviewer import Finding, ReviewResult


def _finding(**overrides) -> Finding:
    defaults = dict(
        file="app.py",
        line=10,
        severity="medium",
        category="bug",
        summary="Something is off.",
        suggestion=None,
    )
    defaults.update(overrides)
    return Finding(**defaults)


def test_choose_event_escalates_to_request_changes_on_high_or_critical():
    assert choose_event([_finding(severity="high")]) == "REQUEST_CHANGES"
    assert choose_event([_finding(severity="critical")]) == "REQUEST_CHANGES"


def test_choose_event_uses_comment_for_low_and_medium_only():
    assert choose_event([_finding(severity="low")]) == "COMMENT"
    assert choose_event([_finding(severity="medium")]) == "COMMENT"


def test_choose_event_uses_comment_when_no_findings():
    assert choose_event([]) == "COMMENT"


def test_choose_event_never_returns_approve():
    # Der Agent ist nur beratend, er darf einen PR nie automatisch approven.
    all_severities = ["critical", "high", "medium", "low"]
    for severity in all_severities:
        assert choose_event([_finding(severity=severity)]) != "APPROVE"
    assert choose_event([]) != "APPROVE"


def test_format_comment_body_includes_suggestion_when_present():
    finding = _finding(suggestion="Add a null check here.")
    body = format_comment_body(finding)
    assert "Add a null check here." in body
    assert "MITTEL" in body


def test_format_comment_body_omits_suggestion_section_when_absent():
    finding = _finding(suggestion=None)
    body = format_comment_body(finding)
    assert "Vorschlag" not in body


def test_format_summary_lists_skipped_files():
    result = ReviewResult(findings=[], overall_assessment="Clean diff.")
    summary = format_summary(result, skipped_files=["huge.py (zu gross)"])
    assert "huge.py (zu gross)" in summary
    assert "keine Probleme gefunden" in summary


def test_format_findings_as_text_includes_file_and_line():
    findings = [_finding(file="src/app.py", line=42)]
    text = format_findings_as_text(findings)
    assert "src/app.py:42" in text
