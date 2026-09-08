"""Schickt einen annotierten PR-Diff an ein Sprachmodell und bekommt strukturierte Funde zurück."""

from __future__ import annotations

from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field

MODEL = "claude-opus-5"
MAX_TOKENS = 8_000

SYSTEM_PROMPT = """Du bist Softwareentwickler:in und übernimmst ein automatisiertes Code-Review für einen GitHub Pull Request.

Der Diff wird dir dateiweise gezeigt, jede Zeile mit ihrer Zeilennummer in \
der NEUEN Version der Datei (rechte Seite) und einer Markierung davor: \
'+' für hinzugefügte Zeilen, '-' für entfernte Zeilen (ohne neue \
Zeilennummer) und keine Markierung für unveränderte Kontextzeilen. Die \
Zeilennummer, die du zurückgibst, MUSS zu einer '+'-Zeile gehören — nie \
zu einer entfernten oder Kontextzeile, und nie erfunden sein.

Prüfe auf:
- Bugs und Korrektheit (Logikfehler, Edge Cases, Off-by-one-Fehler, Race Conditions, fehlende Null-Prüfungen)
- Sicherheitsprobleme (Injection, unsicheres Deserialisieren, hartcodierte Secrets, fehlende Validierung/Auth, Path Traversal)
- Fehlende oder unzureichende Testabdeckung für die geänderte Logik
- Wartbarkeit: Probleme, die Lesbarkeit oder Korrektheit spürbar verschlechtern (keine reinen Stil-Nitpicks)

Melde nur echte, konkrete Probleme auf Zeilen, die in diesem Diff \
tatsächlich hinzugefügt oder geändert wurden. Erfinde keine \
hypothetischen Probleme und kommentiere nichts, was du nicht sehen \
kannst. Wenn der Diff einer Datei gekürzt oder weggelassen wurde, rate \
nicht über ihren Inhalt. Schreibe alle Texte (Zusammenfassung, \
Beschreibung, Vorschlag) auf Deutsch. Wenn du nichts Wesentliches \
findest, gib eine leere Liste zurück und sag das auch so in der \
Gesamteinschätzung."""


class Finding(BaseModel):
    file: str = Field(description="Der exakte Dateipfad aus dem Diff.")
    line: int = Field(
        description="Die Zeilennummer in der neuen Datei, auf die sich der Fund bezieht; muss eine im Diff gezeigte '+'-Zeile sein."
    )
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal["bug", "security", "test-coverage", "maintainability", "performance"]
    summary: str = Field(description="Ein bis zwei Sätze, die das Problem beschreiben.")
    suggestion: Optional[str] = Field(
        default=None, description="Ein konkreter Verbesserungsvorschlag, falls sinnvoll."
    )


class ReviewResult(BaseModel):
    findings: list[Finding]
    overall_assessment: str = Field(
        description="Eine kurze (2-4 Sätze) Gesamteinschätzung der Änderung und des Review-Ergebnisses."
    )


def review_diff(annotated_diff: str, api_key: str) -> ReviewResult:
    """Schickt den annotierten Diff an das Sprachmodell und liefert validierte, strukturierte Funde zurück."""
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.parse(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Bewerte diesen Pull-Request-Diff:\n\n{annotated_diff}",
            }
        ],
        output_format=ReviewResult,
    )
    return response.parsed_output
