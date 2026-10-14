"""
Render a structured meeting-analysis dict into a Markdown notes document.

Pure functions, no I/O. `render(analysis, lang)` supports "is" and "en".
"""

# Section labels per language.
LABELS = {
    "is": {
        "title": "Fundargerð",
        "summary": "Yfirlit",
        "attendees": "Þátttakendur",
        "topics": "Umræðuefni",
        "decisions": "Ákvarðanir",
        "action_items": "Aðgerðir",
        "open_questions": "Opnar spurningar",
        "next_steps": "Næstu skref",
        "none": "_Ekkert skráð._",
        "task": "Verk",
        "owner": "Ábyrgð",
        "due": "Frestur",
        "priority": "Forgangur",
        "unassigned": "—",
    },
    "en": {
        "title": "Meeting Notes",
        "summary": "Summary",
        "attendees": "Attendees",
        "topics": "Topics",
        "decisions": "Decisions",
        "action_items": "Action items",
        "open_questions": "Open questions",
        "next_steps": "Next steps",
        "none": "_None recorded._",
        "task": "Task",
        "owner": "Owner",
        "due": "Due",
        "priority": "Priority",
        "unassigned": "—",
    },
}


def _bullets(items, none_label):
    if not items:
        return none_label
    return "\n".join(f"- {str(item).strip()}" for item in items if str(item).strip()) or none_label


def _topics(topics, none_label):
    if not topics:
        return none_label
    out = []
    for t in topics:
        title = str(t.get("title", "")).strip() or "—"
        notes = str(t.get("notes", "")).strip()
        out.append(f"- **{title}**" + (f" — {notes}" if notes else ""))
    return "\n".join(out) or none_label


def _action_table(items, L):
    if not items:
        return L["none"]
    header = f"| {L['task']} | {L['owner']} | {L['due']} | {L['priority']} |\n|---|---|---|---|"
    rows = []
    for a in items:
        task = str(a.get("task", "")).strip() or "—"
        owner = str(a.get("owner", "")).strip() or L["unassigned"]
        due = str(a.get("due", "")).strip() or L["unassigned"]
        prio = str(a.get("priority", "")).strip() or L["unassigned"]
        # Escape pipes so the table doesn't break
        cells = [c.replace("|", "\\|") for c in (task, owner, due, prio)]
        rows.append("| " + " | ".join(cells) + " |")
    return header + "\n" + "\n".join(rows)


def render(analysis: dict, lang: str, meeting_title: str = None, source_file: str = None) -> str:
    """Render one analysis dict into a Markdown document for the given language ('is'/'en')."""
    if lang not in LABELS:
        raise ValueError(f"Unsupported lang '{lang}' (use 'is' or 'en')")
    L = LABELS[lang]

    heading = meeting_title or L["title"]
    parts = [f"# {heading}"]
    if source_file:
        parts.append(f"_{source_file}_")

    summary = str(analysis.get("summary", "")).strip() or L["none"]

    parts += [
        f"\n## {L['summary']}\n{summary}",
        f"\n## {L['attendees']}\n{_bullets(analysis.get('attendees', []), L['none'])}",
        f"\n## {L['topics']}\n{_topics(analysis.get('topics', []), L['none'])}",
        f"\n## {L['decisions']}\n{_bullets(analysis.get('decisions', []), L['none'])}",
        f"\n## {L['action_items']}\n{_action_table(analysis.get('action_items', []), L)}",
        f"\n## {L['open_questions']}\n{_bullets(analysis.get('open_questions', []), L['none'])}",
        f"\n## {L['next_steps']}\n{_bullets(analysis.get('next_steps', []), L['none'])}",
    ]
    return "\n".join(parts) + "\n"
