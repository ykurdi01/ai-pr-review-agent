"""Wandelt GitHubs rohe Unified-Diff-Patches in einen zeilennummerierten Diff um.

Diese Annotation ist der Grund, warum das Modell Funde auf echten,
überprüfbaren Zeilennummern melden kann, statt zu raten: Jede "+"-Zeile
(hinzugefügt) wird mit ihrer Zeilennummer in der neuen Dateiversion
versehen — genau das, was die Review-Kommentar-API von GitHub für
Inline-Kommentare erwartet.
"""

from __future__ import annotations

MAX_TOTAL_CHARS = 60_000
MAX_FILE_PATCH_CHARS = 12_000


def _annotate_patch(patch: str) -> str:
    """Annotiert den Unified-Diff einer einzelnen Datei mit Zeilennummern der neuen Version."""
    lines_out: list[str] = []
    new_line = 0
    old_line = 0

    for raw_line in patch.splitlines():
        if raw_line.startswith("@@"):
            new_line, old_line = _parse_hunk_header(raw_line, new_line, old_line)
            lines_out.append(raw_line)
        elif raw_line.startswith("\\"):
            # z. B. "\ No newline at end of file" — keine echte Zeile, nicht mitzählen.
            lines_out.append(f"{'':>6}   {raw_line}")
        elif raw_line.startswith("+"):
            new_line += 1
            lines_out.append(f"{new_line:>6} + {raw_line[1:]}")
        elif raw_line.startswith("-"):
            old_line += 1
            lines_out.append(f"{'':>6} - {raw_line[1:]}")
        else:
            new_line += 1
            old_line += 1
            content = raw_line[1:] if raw_line.startswith(" ") else raw_line
            lines_out.append(f"{new_line:>6}   {content}")

    return "\n".join(lines_out)


def _parse_hunk_header(header_line: str, new_line: int, old_line: int) -> tuple[int, int]:
    """Liest die Start-Zeilennummern (neu/alt) aus einem "@@ -a,b +c,d @@"-Header."""
    try:
        header = header_line.split("@@")[1].strip()
        old_part, new_part = header.split(" ")[:2]
        new_line = int(new_part.lstrip("+").split(",")[0]) - 1
        old_line = int(old_part.lstrip("-").split(",")[0]) - 1
    except (IndexError, ValueError):
        # Kaputter Hunk-Header — laufende Zähler einfach beibehalten statt abzustürzen.
        pass
    return new_line, old_line


def build_annotated_diff(files: list[dict]) -> tuple[str, list[str]]:
    """Baut aus der GitHub-"PR-Dateien"-API-Antwort einen zusammenhängenden annotierten Diff.

    Gibt (annotierter_diff_text, übersprungene_dateien) zurück —
    übersprungene_dateien listet jede ausgelassene Datei (gelöscht,
    binär oder zu groß) samt Grund auf, damit das im
    Zusammenfassungs-Kommentar sichtbar wird.
    """
    parts: list[str] = []
    skipped: list[str] = []
    total_chars = 0

    for f in files:
        filename = f.get("filename", "<unbekannt>")
        status = f.get("status", "modified")
        patch = f.get("patch")

        if status == "removed":
            skipped.append(f"{filename} (gelöscht — nicht reviewt)")
            continue
        if patch is None:
            skipped.append(f"{filename} (binär oder zu groß für einen Diff)")
            continue
        if len(patch) > MAX_FILE_PATCH_CHARS:
            skipped.append(f"{filename} (Diff zu groß: {len(patch)} Zeichen)")
            continue
        if total_chars + len(patch) > MAX_TOTAL_CHARS:
            skipped.append(f"{filename} (übersprungen — Review-Budget erreicht)")
            continue

        annotated = _annotate_patch(patch)
        parts.append(f"### Datei: {filename} ({status})\n```diff\n{annotated}\n```")
        total_chars += len(patch)

    return "\n\n".join(parts), skipped
