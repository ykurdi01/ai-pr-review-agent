# PR-Review-Agent

Ein kleines Projekt, das den nervigen Teil des Code-Reviews automatisiert.
Bei jedem Pull Request liest ein GitHub-Actions-Workflow den Diff aus,
schickt ihn an ein Sprachmodell (Anthropic API) und postet die
Rückmeldungen direkt als echten PR-Review, mit Inline-Kommentaren auf den
betroffenen Zeilen und einer kurzen Zusammenfassung obendrüber.

Kein eigener Server, kein Hosting nötig, das läuft komplett innerhalb von
GitHub Actions, zusammen mit dem Code, den es reviewt.

## Was wird geprüft?

Für jede geänderte Datei im PR fragt der Agent das Sprachmodell nach folgenden Punkten.

- **Bugs**, also Logikfehler, Edge Cases, Off-by-one-Fehler und Race Conditions
- **Sicherheitsprobleme** wie Injection, unsicheres Deserialisieren,
  hartcodierte Secrets, fehlende Validierung und Path Traversal
- **Fehlende Testabdeckung**, also geänderte Logik ohne passende Tests
- **Wartbarkeit**, konkret Dinge, die Lesbarkeit oder Korrektheit wirklich
  beeinträchtigen (keine reinen Stil-Nitpicks)

Jeder Fund bekommt einen Schweregrad (`critical` / `high` / `medium` /
`low`), eine Kategorie, eine kurze Erklärung und, wenn möglich, einen
konkreten Verbesserungsvorschlag.

## Wie es funktioniert

```
PR wird geöffnet / aktualisiert
        │
        ▼
.github/workflows/pr-review.yml   (GitHub Actions)
        │
        ▼
GitHub REST API   ──►  geänderte Dateien des PRs abrufen (Unified Diffs)
        │
        ▼
diff_utils.py   ──►  jede Diff-Zeile mit ihrer echten Zeilennummer versehen
        │              (damit Kommentare später auf der richtigen Zeile
        │               landen)
        ▼
reviewer.py   ──►  ein Sprachmodell bewertet den annotierten Diff und
        │           liefert strukturierte Ergebnisse zurück
        │           (Pydantic-validiertes JSON statt Freitext, über
        │           Structured Outputs)
        ▼
github_client.py   ──►  POST /pulls/{n}/reviews
        │                  ein Inline-Kommentar pro Fund, auf der Zeile,
        │                  auf die er sich bezieht, plus ein
        │                  zusammenfassender Kommentar mit dem Gesamturteil
        ▼
Der Pull Request hat jetzt echte Review-Kommentare vom Agenten
```

Der Agent **approved PRs nie automatisch**, er kommentiert nur
(`COMMENT`) oder fordert Änderungen an (`REQUEST_CHANGES`), wenn er einen
kritischen oder schwerwiegenden Fund hat. Er bleibt beratend, wie ein
menschlicher Reviewer, der Kommentare hinterlässt.

## Setup

1. **API-Key als Repository-Secret hinterlegen.**
   Repo → Settings → Secrets and variables → Actions → *New repository
   secret*, Name `AI_API_KEY`.
   (`GITHUB_TOKEN` wird von GitHub Actions automatisch bereitgestellt,
   dafür muss nichts eingerichtet werden.)

2. **Das war's schon.** Der Workflow in
   [`.github/workflows/pr-review.yml`](.github/workflows/pr-review.yml)
   läuft automatisch bei jedem `pull_request`-Event (opened, updated,
   reopened). Einfach einen PR öffnen und den Check "PR-Review"
   beobachten.

## Lokal ausprobieren

```bash
git clone https://github.com/ykurdi01/ai-pr-review-agent.git
cd ai-pr-review-agent
pip install -e ".[dev]"

cp .env.example .env   # AI_API_KEY, GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER eintragen
export $(grep -v '^#' .env | xargs)   # oder z. B. mit python-dotenv / direnv

pr-review-agent
```

## Projektstruktur

```
src/pr_review_agent/
  diff_utils.py     # GitHub-Patch → zeilennummerierter Diff
  reviewer.py        # Sprachmodell-Aufruf + Pydantic-Schema für die Funde
  formatting.py      # Funde → GitHub-Markdown
  github_client.py   # schlanker Wrapper um die GitHub REST API
  main.py             # Einstiegspunkt / Ablaufsteuerung
tests/                 # Unit-Tests (Sprachmodell- und GitHub-Aufrufe sind gemockt)
.github/workflows/
  pr-review.yml        # der eigentliche Agent, läuft bei jedem PR
  ci.yml                 # führt die Tests bei jedem Push/PR aus
```

## Tests ausführen

```bash
pip install -e ".[dev]"
pytest -q
```

Die Tests mocken sowohl den Sprachmodell-Client als auch die GitHub-API,
es braucht also weder Internetzugang noch echte API-Keys.

## Einschränkungen

- Reviewt wird nur der *Diff*, nicht die ganze Datei, wie bei jemandem,
  der schnell drüberschaut, können dadurch Dinge übersehen werden, die
  nur im größeren Kontext auffallen würden.
- Sehr große Diffs werden gekürzt (siehe `diff_utils.MAX_TOTAL_CHARS`),
  damit ein Review nicht zu viele Tokens verbraucht; übersprungene
  Dateien werden in der Zusammenfassung aufgelistet.
- Der Agent ist eine Unterstützung, kein Ersatz für ein menschliches
  Review, eher ein schneller erster Blick.

## Lizenz

[MIT](LICENSE)
