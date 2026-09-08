from unittest.mock import MagicMock, patch

from pr_review_agent.reviewer import Finding, ReviewResult, review_diff


def _fake_review_result() -> ReviewResult:
    return ReviewResult(
        findings=[
            Finding(
                file="app.py",
                line=3,
                severity="medium",
                category="bug",
                summary="Off-by-one in loop bound.",
                suggestion="Use range(len(items)) instead of range(len(items) + 1).",
            )
        ],
        overall_assessment="One medium-severity bug found; otherwise looks fine.",
    )


def test_review_diff_returns_the_parsed_output():
    fake_result = _fake_review_result()
    fake_response = MagicMock()
    fake_response.parsed_output = fake_result

    with patch("pr_review_agent.reviewer.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.parse.return_value = fake_response

        result = review_diff("### File: app.py\n```diff\n1 + foo\n```", api_key="test-key")

    mock_client_cls.assert_called_once_with(api_key="test-key")
    assert result is fake_result
    assert result.findings[0].severity == "medium"
    assert result.findings[0].category == "bug"


def test_review_diff_calls_model_with_structured_output_format():
    fake_response = MagicMock()
    fake_response.parsed_output = ReviewResult(findings=[], overall_assessment="Looks good.")

    with patch("pr_review_agent.reviewer.anthropic.Anthropic") as mock_client_cls:
        mock_parse = mock_client_cls.return_value.messages.parse
        mock_parse.return_value = fake_response

        review_diff("some diff", api_key="test-key")

    _, kwargs = mock_parse.call_args
    assert kwargs["output_format"] is ReviewResult
    assert kwargs["model"] == "claude-opus-5"
