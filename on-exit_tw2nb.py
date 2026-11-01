#!/usr/bin/env python3
"""
on-exit_tw2nb.py - Mirror task status into nb tasknotes
Version: 1.3.0

After Taskwarrior has written its changes, runs `nb tw status <uuid>` (nb-plugins
tw.nb-plugin) for every added or modified task that links an nb note by path
(`nb: tasknotes:kitchen/x-1a2b3c4d.note.md`). tw2nb's own numeric archive links
(`nb: tasks:42`) and tasks without an `nb:` annotation cost nothing.

on-exit, not on-modify: on-modify runs before the change is written, so the
plugin's `task export` would still see the old status.

Never blocks or fails a task command — problems go to stderr only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NUMERIC_LINK = re.compile(r'^nb: [\w.-]+:\d+$')


def links_a_note(task: dict) -> bool:
    return any(a.get('description', '').startswith('nb: ') and
               not NUMERIC_LINK.match(a.get('description', '').strip())
               for a in task.get('annotations', []))


def main() -> int:
    lines = sys.stdin.read().splitlines()
    nb = shutil.which('nb')
    plugin = Path(os.environ.get('NB_DIR') or Path.home() / '.nb') / '.plugins' / 'tw.nb-plugin'
    if not nb or not plugin.exists():
        return 0
    seen = set()
    for line in lines:
        try:
            task = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        uuid = task.get('uuid') if isinstance(task, dict) else None
        if not uuid or uuid in seen or not links_a_note(task):
            continue
        seen.add(uuid)
        try:
            r = subprocess.run([nb, 'tw', 'status', uuid], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60)
            if r.returncode != 0:
                print(f'[tw2nb] nb tw status {uuid[:8]}: {r.stderr.strip()}', file=sys.stderr)
        except Exception as e:                       # never fail the task command
            print(f'[tw2nb] nb tw status {uuid[:8]}: {e}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
