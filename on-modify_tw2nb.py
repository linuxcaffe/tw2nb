#!/usr/bin/env python3
"""
on-modify_tw2nb.py - Archive Taskwarrior task events to nb
Version: 0.1.0

Triggered on every task modification. Detects three archivable events:
  completed  - task marked done
  deleted    - task deleted (if tw2nb.on_delete=yes)
  annotated  - new annotation added to an active task

On completion: also annotates the task with the nb note reference
(e.g. 'nb: tasks:42') so the breadcrumb lives in the task record.

Never blocks the task operation — errors go to stderr only.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ============================================================================
# Locate tw2nb_lib (dev dir first, then installed location)
# ============================================================================

_lib_dirs = [
    Path(__file__).parent,                      # dev: ~/dev/tw2nb/
    Path.home() / '.task' / 'scripts',          # installed
]
for _d in _lib_dirs:
    if (_d / 'tw2nb_lib.py').exists():
        sys.path.insert(0, str(_d))
        break

from tw2nb_lib import archive, load_config  # noqa: E402

CONFIG_FILE = Path.home() / '.task' / 'config' / 'tw2nb.rc'
NB          = '/usr/local/bin/nb'


# ============================================================================
# Event detection
# ============================================================================

def detect_event(original: dict, modified: dict) -> Optional[str]:
    orig_s = original.get('status', '')
    mod_s  = modified.get('status', '')

    if orig_s not in ('completed', 'deleted') and mod_s == 'completed':
        return 'completed'
    if orig_s not in ('completed', 'deleted') and mod_s == 'deleted':
        return 'deleted'

    # Annotation added to an active (non-terminal) task
    if mod_s not in ('completed', 'deleted'):
        orig_n = len(original.get('annotations', []))
        mod_n  = len(modified.get('annotations', []))
        if mod_n > orig_n:
            return 'annotated'

    return None


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    # on-modify receives two JSON lines: original then modified
    lines = []
    for line in sys.stdin:
        line = line.strip()
        if line:
            lines.append(line)
        if len(lines) == 2:
            break

    if len(lines) < 2:
        # Malformed input — pass through whatever we got
        if lines:
            print(lines[0])
        return 0

    original = json.loads(lines[0])
    modified = json.loads(lines[1])

    event = detect_event(original, modified)

    if event is None:
        print(json.dumps(modified))
        return 0

    cfg = load_config(CONFIG_FILE)

    if event == 'deleted' and not cfg['on_delete']:
        print(json.dumps(modified))
        return 0

    # Archive — errors must not block the task operation
    note_ref = None
    try:
        note_ref = archive(modified, event, cfg)
    except Exception as e:
        print(f'[tw2nb] WARNING: archival failed: {e}', file=sys.stderr)

    # On completion, add nb breadcrumb annotation to the task
    if event == 'completed' and note_ref:
        from datetime import datetime
        ann = {
            'entry':       datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'),
            'description': f'nb: {note_ref}',
        }
        modified.setdefault('annotations', []).append(ann)

    # Output the (possibly modified) task — Taskwarrior commits this
    print(json.dumps(modified))

    # nb sync after output (never delays task commit)
    if cfg['sync']:
        try:
            subprocess.run(
                [NB, 'sync', f"{cfg['notebook']}:"],
                capture_output=True, timeout=30,
            )
        except Exception:
            pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
