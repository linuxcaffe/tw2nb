# tw2nb

Archives Taskwarrior task events to [nb](https://xwmx.github.io/nb/) as structured todo notes and a running daily journal.

## What it does

On three triggering events:

| Event | Trigger | Action |
|-------|---------|--------|
| `completed` | `task done` | Create/close nb todo · journal entry · annotate task with nb ref |
| `deleted` | `task delete` | Archive to nb · journal entry (if `on_delete=yes`) |
| `annotated` | new annotation on active task | Append to task note (journal entry if `journal_annotated=yes`) |

**Per-task note** (`tasks:` notebook) — one nb todo per task, updated on each event. Full annotation history. Closed automatically on completion.

**Running journal** (`home:` notebook) — dated entries (`2026-03-02.md`) with completed/deleted tasks alongside any other nb content. Grouped by day.

## Note format

### Journal entry (completed task)

```markdown
## ✅ Fix the login bug
> #project/work/web #bug
> `abc12345` · created 2026-02-28 · done 2026-03-02 (3d)

[→ task note](tasks:42)

---
```

### Task note (per-UUID nb todo)

```markdown
# [ ] Fix the login bug
#project/work/web #bug

**UUID:** `abc12345`
**Project:** work.web
**Priority:** H
**Created:** 2026-02-28

---

## 2026-03-01 — Annotation added 📝

*2026-03-01 — Found culprit in auth middleware*

## 2026-03-02 — Completed ✅
*Duration: 3d*

### Annotations

1. **2026-02-28** — Started investigating...
2. **2026-03-01** — Found culprit in auth middleware
3. **2026-03-02** — Fixed and deployed ✓
```

## Tag mapping

| Taskwarrior | nb |
|-------------|-----|
| `+bug` | `#bug` |
| `project:work.web` | `#project/work/web` |

## Installation

```bash
# 1. Create the nb tasks notebook
nb notebooks add tasks

# 2. Run the installer
bash tw2nb.install

# 3. Edit config
$EDITOR ~/.task/config/tw2nb.rc

# 4. Test
task <id> done
nb tasks: list
```

## Config (`~/.task/config/tw2nb.rc`)

```ini
tw2nb.notebook          = tasks   # nb notebook for per-task todos
tw2nb.journal           = home    # nb notebook for running journal
tw2nb.on_delete         = no      # archive deleted tasks too (yes/no)
tw2nb.journal_annotated = no      # also journal annotation events (yes/no)
tw2nb.sync              = no      # run 'nb sync' after each archive (yes/no)
tw2nb.project_notebooks = no      # one notebook per TW project (yes/no)
```

### journal_annotated

When `no` (default): annotations update the per-task note only. The journal stays clean as a "what finished today" log.

When `yes`: each new annotation also adds a brief `📝` entry to the journal. Note that completing an annotated task will then produce two journal entries for that task on the same day — the annotation event and the completion event.

## Retrospective backfill

Archive completed tasks that predate the hook installation:

```bash
# Preview what would be archived
tw2nb-retro --dry-run

# Archive all completed tasks
tw2nb-retro

# Archive tasks completed since a specific date
tw2nb-retro --from 2026-01-01

# Archive deleted tasks too
tw2nb-retro --status all

# Verbose output
tw2nb-retro -v
```

Safe to re-run — skips tasks already present in nb (keyed by uuid8).

## Querying your archive

```bash
nb tasks: list                          # all task notes
nb todos --closed                       # completed tasks
nb search "#project/work/web"           # by project
nb search "#bug"                        # by tag
nb search "abc12345"                    # by uuid8
nb home: list                           # journal entries
nb browse                               # web UI
```

## Git / sync

nb auto-commits every operation. To push to a remote:

```bash
nb set tasks git_push_remote origin
# then enable sync in tw2nb.rc:
# tw2nb.sync = yes
```

Or run `nb sync` manually.

## Files

| File | Installed to |
|------|-------------|
| `on-modify_tw2nb.py` | `~/.task/hooks/` |
| `tw2nb_lib.py` | `~/.task/scripts/` |
| `tw2nb-retro` | `~/.task/scripts/` |
| `tw2nb.rc` | `~/.task/config/` |
