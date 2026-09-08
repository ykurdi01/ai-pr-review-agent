"""Schlanker Wrapper um die GitHub REST API für das, was der Agent braucht:
die geänderten Dateien eines PRs lesen und ein strukturiertes Review zurückposten.
"""

from __future__ import annotations

from typing import Any

import requests

from .formatting import choose_event, format_comment_body, format_findings_as_text, format_summary
from .reviewer import ReviewResult

API_BASE = "https://api.github.com"


class GitHubClient:
    def __init__(self, token: str, owner: str, repo: str) -> None:
        self._owner = owner
        self._repo = repo
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _url(self, path: str) -> str:
        return f"{API_BASE}/repos/{self._owner}/{self._repo}{path}"

    def get_pull_request(self, pr_number: int) -> dict[str, Any]:
        resp = self._session.get(self._url(f"/pulls/{pr_number}"))
        resp.raise_for_status()
        return resp.json()

    def get_pull_request_files(self, pr_number: int) -> list[dict[str, Any]]:
        """Paginiert durch alle geänderten Dateien des PRs."""
        files: list[dict[str, Any]] = []
        page = 1
        while True:
            resp = self._session.get(
                self._url(f"/pulls/{pr_number}/files"),
                params={"per_page": 100, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return files

    def post_review(
        self,
        pr_number: int,
        commit_id: str,
        result: ReviewResult,
        skipped_files: list[str],
    ) -> None:
        """Postet das Review als Inline-Kommentare + Zusammenfassung. Fällt auf
        ein reines Zusammenfassungs-Review zurück, falls ein Inline-Kommentar
        sich auf eine Zeile bezieht, die GitHub ablehnt (z. B. eine erfundene
        Zeilennummer außerhalb des Diff-Kontexts).
        """
        event = choose_event(result.findings)
        body = format_summary(result, skipped_files)
        comments = [
            {
                "path": f.file,
                "line": f.line,
                "side": "RIGHT",
                "body": format_comment_body(f),
            }
            for f in result.findings
        ]

        payload: dict[str, Any] = {"commit_id": commit_id, "body": body, "event": event}
        if comments:
            payload["comments"] = comments

        resp = self._session.post(self._url(f"/pulls/{pr_number}/reviews"), json=payload)
        if resp.status_code < 300:
            return

        # Platzierung des Inline-Kommentars fehlgeschlagen (meist: eine Zeile
        # gehört nicht zum von GitHub erfassten Diff-Hunk). Erneuter Versuch
        # als reines Zusammenfassungs-Review, damit der Lauf trotzdem
        # erfolgreich ist und die Funde nicht verloren gehen.
        fallback_body = (
            f"{body}\n\n"
            f"> ⚠️ Inline-Kommentare konnten nicht gepostet werden (HTTP {resp.status_code}); "
            "die Funde werden stattdessen unten aufgelistet.\n\n"
            f"{format_findings_as_text(result.findings)}"
        )
        fallback_payload = {"commit_id": commit_id, "body": fallback_body, "event": event}
        fallback_resp = self._session.post(
            self._url(f"/pulls/{pr_number}/reviews"), json=fallback_payload
        )
        fallback_resp.raise_for_status()
