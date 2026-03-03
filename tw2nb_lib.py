#!/usr/bin/env python3
"""
tw2nb_lib.py - Shared library for tw2nb hook and retro script
Version: 0.1.0

Handles formatting of Taskwarrior task data into nb-compatible markdown,
and all nb subprocess operations (create, append, close, journal).

Install location: ~/.task/scripts/tw2nb_lib.py
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

NB = '/usr/local/bin/nb'


# ============================================================================
# Config
# ============================================================================

def load_config(config_file) -> dict:
    """Load tw2nb settings from .rc file, with defaults."""
    cfg_path = Path(config_file)

    def get(key, default):
        if not cfg_path.exists():
            return default
        with cfg_path.open() as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                if k.strip() == key:
                    return v.split('#')[0].strip() or default
        return default

    return {
        'notebook':           get('tw2nb.notebook',           'tasks'),
        'journal':            get('tw2nb.journal',            'home'),
        'on_delete':          get('tw2nb.on_delete',          'no') == 'yes',
        'journal_annotated':  get('tw2nb.journal_annotated',  'no') == 'yes',
        'sync':               get('tw2nb.sync',               'no') == 'yes',
        'project_notebooks':  get('tw2nb.project_notebooks',  'no') == 'yes',
    }


# ============================================================================
# nb subprocess helpers
# ============================================================================

def run_nb(*args, input_text=None, timeout=20) -> subprocess.CompletedProcess:
    return subprocess.run(
        [NB] + list(args),
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _parse_note_id(output: str) -> Optional[str]:
    """Extract note ID from nb output like '[42]' or '[tasks:42]'."""
    match = re.search(r'\[(?:\w[\w-]*:)?(\d+)\]', output)
    return match.group(1) if match else None


def find_task_note(notebook: str, uuid8: str) -> Optional[str]:
    """Search nb for an existing task note by uuid8. Returns note ID or None.

    Uses 'nb {notebook}: search' to scope the search to the right notebook.
    """
    result = run_nb(f'{notebook}:', 'search', uuid8, '--no-color', '--list')
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            note_id = _parse_note_id(line)
            if note_id:
                return note_id
    return None


def create_task_note(notebook: str, task: dict, tags: str, content: str) -> Optional[str]:
    """Create a new nb todo for this task. Returns note ID or None.

    nb todos add takes title as a positional arg (no --title flag).
    Notebook is scoped via 'nb {notebook}: todos add' pattern.
    Falls back to plain nb add if todos add fails.
    """
    title = task.get('description', 'Untitled task')

    # Primary: nb todo (singular) in the scoped notebook
    tag_args = ['--tags', tags] if tags else []
    result = run_nb(f'{notebook}:', 'todos', 'add', title, *tag_args, '--content', content, '--no-color')
    if result.returncode == 0:
        note_id = _parse_note_id(result.stdout)
        if note_id:
            return note_id

    # Fallback: plain note (still scoped to notebook)
    result2 = run_nb(f'{notebook}:', 'add', '--title', title, *tag_args, '--content', content, '--no-color')
    if result2.returncode == 0:
        note_id = _parse_note_id(result2.stdout)
        if note_id:
            return note_id

    print(f'[tw2nb] WARNING: could not create note in {notebook}:', file=sys.stderr)
    return None


def append_to_note(notebook: str, note_id: str, section: str):
    """Append a section to an nb note by writing the file directly and git-committing."""
    path_result = run_nb('show', f'{notebook}:{note_id}', '--path')
    if path_result.returncode != 0 or not path_result.stdout.strip():
        print(f'[tw2nb] WARNING: could not get path for note {notebook}:{note_id}', file=sys.stderr)
        return
    note_path = Path(path_result.stdout.strip())
    with note_path.open('a') as f:
        f.write('\n' + section + '\n')
    subprocess.run(
        ['git', '-C', str(note_path.parent), 'commit', '-a', '-m', 'tw2nb: append note'],
        capture_output=True, text=True,
    )


def close_task_todo(notebook: str, note_id: str):
    """Mark an nb todo as done.

    'nb todo done' (singular) is the action; 'nb todos done' (plural) lists closed todos.
    """
    result = run_nb('todo', 'do', f'{notebook}:{note_id}', '--no-color')
    if result.returncode != 0:
        print(
            f'[tw2nb] WARNING: could not close todo {notebook}:{note_id}'
            + (f': {result.stderr.strip()}' if result.stderr.strip() else ''),
            file=sys.stderr,
        )


def find_journal_note(journal: str, date: str) -> Optional[str]:
    """Find today's journal note by date string. Returns note ID or None."""
    result = run_nb(f'{journal}:', 'search', date, '--no-color', '--list')
    if result.returncode == 0 and result.stdout.strip():
        for line in result.stdout.strip().split('\n'):
            if date in line:
                note_id = _parse_note_id(line)
                if note_id:
                    return note_id
    return None


def append_to_journal(journal: str, date: str, entry: str):
    """Append entry to today's journal note, creating it if needed."""
    note_id = find_journal_note(journal, date)
    if note_id:
        append_to_note(journal, note_id, entry)
    else:
        run_nb(f'{journal}:', 'add', '--title', date, '--tags', '#taskwarrior', '--content', entry)


# ============================================================================
# Formatting helpers
# ============================================================================

def format_tags(task: dict) -> str:
    """Build nb #tag string from TW tags and project.

    project.home.garden  →  #project/home/garden
    +tag                 →  #tag
    """
    tags = []
    project = task.get('project', '')
    if project:
        tags.append('#project/' + project.replace('.', '/'))
    for tag in task.get('tags', []):
        tags.append(f'#{tag}')
    return ' '.join(tags)


def format_date(tw_date: str) -> str:
    """Convert Taskwarrior ISO date (20260302T143000Z) to YYYY-MM-DD."""
    if not tw_date:
        return ''
    try:
        return datetime.strptime(tw_date[:8], '%Y%m%d').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return tw_date


def duration_str(entry: str, end: str) -> str:
    """Human-readable duration between two TW dates, e.g. '3d' or '2w 1d'."""
    try:
        s = datetime.strptime(entry[:8], '%Y%m%d')
        e = datetime.strptime(end[:8], '%Y%m%d')
        days = (e - s).days
        if days < 1:
            return 'same day'
        if days < 14:
            return f'{days}d'
        weeks, rem = divmod(days, 7)
        return f'{weeks}w {rem}d' if rem else f'{weeks}w'
    except (ValueError, TypeError):
        return ''


def format_annotations(task: dict) -> str:
    """Numbered markdown list of all annotations."""
    anns = task.get('annotations', [])
    if not anns:
        return ''
    lines = []
    for i, ann in enumerate(anns, 1):
        date = format_date(ann.get('entry', ''))
        desc = ann.get('description', '')
        lines.append(f'{i}. **{date}** — {desc}')
    return '\n'.join(lines)


# ============================================================================
# Note formatting
# ============================================================================

def format_task_note_header(task: dict, tags: str) -> str:
    """Metadata block passed as --content when creating a per-UUID task note.

    nb generates its own '# [x] title' and '## Tags' section from the todo
    structure and --tags argument. Content starts directly with UUID metadata.
    """
    uuid8    = task.get('uuid', '')[:8]
    project  = task.get('project', '')
    priority = task.get('priority', '')
    entry    = format_date(task.get('entry', ''))
    due      = format_date(task.get('due', ''))

    meta = [f'**UUID:** `{uuid8}`']
    if project:  meta.append(f'**Project:** {project}')
    if priority: meta.append(f'**Priority:** {priority}')
    if entry:    meta.append(f'**Created:** {entry}')
    if due:      meta.append(f'**Due:** {due}')
    return '  \n'.join(meta) + '\n\n---'


def format_event_section(task: dict, event: str, today: str) -> str:
    """Dated section appended to the per-UUID task note on each event."""
    anns_text = format_annotations(task)

    if event == 'completed':
        dur = duration_str(task.get('entry', ''), task.get('end', ''))
        dur_line = f'  \n*Duration: {dur}*' if dur else ''
        header = f'## {today} — Completed ✅{dur_line}'
    elif event == 'deleted':
        header = f'## {today} — Deleted 🗑'
    else:  # annotated
        header = f'## {today} — Annotation added 📝'

    lines = [header, '']
    if anns_text:
        if event in ('completed', 'deleted'):
            lines += ['### Annotations', '', anns_text]
        else:
            # Just the latest annotation
            last = task.get('annotations', [{}])[-1]
            date = format_date(last.get('entry', ''))
            desc = last.get('description', '')
            lines.append(f'*{date} — {desc}*')

    return '\n'.join(lines)


def format_journal_entry(task: dict, event: str, today: str, note_ref: Optional[str]) -> str:
    """Compact entry appended to today's running journal note."""
    desc     = task.get('description', 'Untitled')
    uuid8    = task.get('uuid', '')[:8]
    tags     = format_tags(task)
    entry_dt = format_date(task.get('entry', ''))

    if event == 'completed':
        end_dt = format_date(task.get('end', ''))
        dur    = duration_str(task.get('entry', ''), task.get('end', ''))
        dur_s  = f' ({dur})' if dur else ''
        heading = f'## ✅ {desc}'
        byline  = f'> {tags}  \n> `{uuid8}` · created {entry_dt} · done {end_dt}{dur_s}'
    elif event == 'deleted':
        heading = f'## 🗑 {desc}'
        byline  = f'> {tags}  \n> `{uuid8}` · created {entry_dt}'
    else:  # annotated
        heading = f'## 📝 {desc}'
        byline  = f'> {tags}  \n> `{uuid8}`'

    note_link = f'[→ task note]({note_ref})' if note_ref else ''

    lines = [heading, byline, '']
    if event == 'annotated':
        last = task.get('annotations', [{}])[-1]
        date = format_date(last.get('entry', ''))
        desc_ann = last.get('description', '')
        lines += [f'*{date} — {desc_ann}*', '']

    if note_link:
        lines += [note_link, '']
    lines.append('---')
    return '\n'.join(lines)


# ============================================================================
# Top-level archive operation (used by hook and retro)
# ============================================================================

def archive(task: dict, event: str, cfg: dict, today: str = None) -> Optional[str]:
    """Archive a task event to nb. Returns 'notebook:id' reference or None.

    Creates or updates the per-UUID task note (nb todo) in cfg['notebook'],
    and appends an entry to the dated journal note in cfg['journal'].
    """
    if today is None:
        today = datetime.now().strftime('%Y-%m-%d')

    notebook = cfg['notebook']
    journal  = cfg['journal']
    uuid     = task.get('uuid', '')
    uuid8    = uuid[:8] if uuid else 'unknown'
    tags     = format_tags(task)

    event_section   = format_event_section(task, event, today)
    journal_entry   = None  # built after we know the note_ref

    # --- Per-UUID task note ---
    note_id = find_task_note(notebook, uuid8)
    if note_id:
        append_to_note(notebook, note_id, event_section)
    else:
        header  = format_task_note_header(task, tags)
        content = header + '\n\n' + event_section
        note_id = create_task_note(notebook, task, tags, content)

    if event == 'completed' and note_id:
        close_task_todo(notebook, note_id)

    note_ref = f'{notebook}:{note_id}' if note_id else None

    # --- Running journal ---
    if event != 'annotated' or cfg.get('journal_annotated'):
        journal_entry = format_journal_entry(task, event, today, note_ref)
        append_to_journal(journal, today, journal_entry)

    return note_ref
