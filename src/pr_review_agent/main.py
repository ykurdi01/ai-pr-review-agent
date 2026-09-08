"""Einstiegspunkt für die Kommandozeile. Liest die Umgebungsvariablen von
GitHub Actions, holt den PR-Diff, lässt ihn von einem Sprachmodell bewerten
und postet das Ergebnis als PR-Review zurück.
"""

from __future__ import annotations

import os
import sys

from .diff_utils import build_annotated_diff
from .github_client import GitHubClient
from .reviewer import review_diff

REQUIRED_ENV_VARS = ("GITHUB_TOKEN", "AI_API_KEY", "GITHUB_REPOSITORY", "PR_NUMBER")


def main() -> int:
    env = {name: os.environ.get(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in env.items() if not value]
    if missing:
        print(f"Fehlende Umgebungsvariable(n): {', '.join(missing)}", file=sys.stderr)
        return 1

    owner, _, repo = env["GITHUB_REPOSITORY"].partition("/")
    if not owner or not repo:
        print(
            f"GITHUB_REPOSITORY muss im Format 'owner/repo' sein, erhalten: {env['GITHUB_REPOSITORY']!r}",
            file=sys.stderr,
        )
        return 1

    try:
        pr_number = int(env["PR_NUMBER"])
    except ValueError:
        print(f"PR_NUMBER muss eine Zahl sein, erhalten: {env['PR_NUMBER']!r}", file=sys.stderr)
        return 1

    gh = GitHubClient(token=env["GITHUB_TOKEN"], owner=owner, repo=repo)

    print(f"Lade PR #{pr_number} von {owner}/{repo}...")
    pr = gh.get_pull_request(pr_number)
    head_sha = pr["head"]["sha"]

    files = gh.get_pull_request_files(pr_number)
    print(f"{len(files)} Datei(en) geändert.")
    if not files:
        print("Nichts zu reviewen.")
        return 0

    annotated_diff, skipped = build_annotated_diff(files)
    if skipped:
        print(f"{len(skipped)} Datei(en) übersprungen: {', '.join(skipped)}")
    if not annotated_diff.strip():
        print("In diesem Diff gibt es nichts zu reviewen (nur gelöschte/binäre/zu große Dateien).")
        return 0

    print("Frage das Sprachmodell nach einem Review...")
    result = review_diff(annotated_diff, api_key=env["AI_API_KEY"])
    print(f"{len(result.findings)} Fund(e) entdeckt.")

    gh.post_review(pr_number, head_sha, result, skipped_files=skipped)
    print("Review gepostet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
