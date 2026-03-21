#!/usr/bin/env python3
"""
on-add_tw2nb.py - Archive tasks logged directly as completed via `task log`
Version: 0.1.0

`task log` creates a task already in completed state, firing on-add rather
than on-modify. This hook detects that case and archives it to nb exactly
as on-modify_tw2nb.py would for a normal completion.

Never blocks the task operation — errors go to stderr only.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ============================================================================
# Locate tw2nb_lib (dev dir first, then installed location)
# ============================================================================

_lib_dirs = [
    Path(__file__).parent,                  # dev: ~/dev/tw2nb/
    Path.home() / '.task' / 'scripts',     # installed
]
for _d in _lib_dirs:
    if (_d / 'tw2nb_lib.py').exists():
        sys.path.insert(0, str(_d))
        break

from tw2nb_lib import archive, load_config  # noqa: E402

CONFIG_FILE = Path.home() / '.task' / 'config' / 'tw2nb.rc'
NB          = '/usr/local/bin/nb'


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    # on-add receives one JSON line: the new task
    line = sys.stdin.readline().strip()
    if not line:
        return 0

    task = json.loads(line)

    # Only act on tasks logged directly as completed (task log)
    if task.get('status') != 'completed':
        print(json.dumps(task))
        return 0

    cfg = load_config(CONFIG_FILE)

    note_ref = None
    try:
        note_ref = archive(task, 'completed', cfg)
    except Exception as e:
        print(f'[tw2nb] WARNING: archival failed: {e}', file=sys.stderr)

    # Add nb breadcrumb annotation — committed with the task
    if note_ref:
        ann = {
            'entry':       datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'),
            'description': f'nb: {note_ref}',
        }
        task.setdefault('annotations', []).append(ann)

    print(json.dumps(task))

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
