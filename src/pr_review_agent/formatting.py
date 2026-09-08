"""Wandelt strukturierte Review-Funde in das Markdown um, das GitHub anzeigt."""

from __future__ import annotations

from .reviewer import Finding, ReviewResult

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}

SEVERITY_LABEL_DE = {
    "critical": "KRITISCH",
    "high": "HOCH",
    "medium": "MITTEL",
    "low": "NIEDRIG",
}

CATEGORY_LABEL_DE = {
    "bug": "Bug",
    "security": "Sicherheit",
    "test-coverage": "Testabdeckung",
    "maintainability": "Wartbarkeit",
    "performance": "Performance",
}

AGENT_SIGNATURE = "_Automatisch gepostet vom PR-Review-Agenten_"


def choose_event(findings: list[Finding]) -> str:
    """Leitet aus den Schweregraden der Funde das GitHub-Review-Urteil ab.

    Gibt nie APPROVE zurück — der Agent ist beratend, kein Gatekeeper.
    """
    if any(f.severity in ("critical", "high") for f in findings):
        return "REQUEST_CHANGES"
    return "COMMENT"


def format_comment_body(finding: Finding) -> str:
    emoji = SEVERITY_EMOJI.get(finding.severity, "⚪")
    severity_label = SEVERITY_LABEL_DE.get(finding.severity, finding.severity.upper())
    category_label = CATEGORY_LABEL_DE.get(finding.category, finding.category)

    lines = [
        f"{emoji} **{severity_label} · {category_label}**",
        "",
        finding.summary,
    ]
    if finding.suggestion:
        lines += ["", f"**Vorschlag:** {finding.suggestion}"]
    lines += ["", AGENT_SIGNATURE]
    return "\n".join(lines)


def format_summary(result: ReviewResult, skipped_files: list[str]) -> str:
    counts: dict[str, int] = {}
    for f in result.findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    order = ["critical", "high", "medium", "low"]
    count_line = (
        ", ".join(f"{counts[s]} × {SEVERITY_LABEL_DE.get(s, s)}" for s in order if s in counts)
        if counts
        else "keine Probleme gefunden"
    )

    parts = [
        "## Review",
        "",
        result.overall_assessment,
        "",
        f"**Funde:** {count_line}",
    ]
    if skipped_files:
        parts += ["", "**Nicht reviewt:**"]
        parts += [f"- {s}" for s in skipped_files]
    parts += ["", AGENT_SIGNATURE]
    return "\n".join(parts)


def format_findings_as_text(findings: list[Finding]) -> str:
    """Text-Fallback, falls Inline-Kommentare nicht gepostet werden können."""
    lines = []
    for f in findings:
        severity_label = SEVERITY_LABEL_DE.get(f.severity, f.severity.upper())
        category_label = CATEGORY_LABEL_DE.get(f.category, f.category)
        lines.append(f"- **{f.file}:{f.line}** [{severity_label}/{category_label}] {f.summary}")
        if f.suggestion:
            lines.append(f"  - Vorschlag: {f.suggestion}")
    return "\n".join(lines)
