- Project: https://github.com/linuxcaffe/tw2nb
- Issues:  https://github.com/linuxcaffe/tw2nb/issues

# tw2nb

Archives completed Taskwarrior tasks to [nb](https://xwmx.github.io/nb/) as searchable todos and a running daily journal.

## TL;DR

- Completed tasks land in nb as closed todos — with tags, annotations, and task notes intact
- `task log` (already-done tasks) archives the same way as `task done`
- A running daily journal records completions, deletions, and annotation events alongside your other notes
- Project-based routing: `tw.gtk` and `tw.sanity` go to a `tw` notebook automatically
- Annotations and annn task notes can go into the journal instead of the per-task note — your choice
- `nb info tasks:42` pulls live Taskwarrior data for any archived task — the round-trip
- `nb g "#project/tw"` searches your archive by project, tag, or UUID across all notebooks
- `tw2nb-retro` backfills tasks that completed before the hook was installed
- Requires Taskwarrior 2.6.2, Python 3.6+, and [nb](https://xwmx.github.io/nb/)

## Why this exists

Taskwarrior is built around the present. Completed tasks get marked done and effectively disappear from view — there is no native way to search your task history by project, browse annotations you added along the way, or see what you accomplished on a given day alongside the rest of your notes.

`task completed` and `task log` can show raw history, but the data is flat, unsearchable by content, and disconnected from any note-taking system. Annotations added over two weeks of work on a task disappear with it on completion. Attached note files stay in `~/.task/notes/`, uncoupled from anything else.

nb solves the archive half of this problem — it is a fast, git-backed, terminal-first note system with todos, tags, full-text search, and a daily journal. What it lacks is any connection to Taskwarrior. tw2nb is that connection.

`nb info` closes the loop in the other direction. From any archived task note or journal page, you can pull up the live Taskwarrior record for every referenced task — one command, no UUID hunting.

## What this means for you

Every task you finish flows automatically into your notes — with its tags, annotations, and attached note files — without any extra steps. Your daily journal becomes a shared space where Taskwarrior completions appear alongside everything else you write. When you want to revisit a task, search your archive by project or tag, or check whether a related task is still active, it is all one command away.

## Core concepts

**Task note** — a per-UUID nb todo, one per Taskwarrior task, created or updated on each archived event. Lives in the configured task notebook, or in a project-derived notebook when `project_notebooks` is enabled.

**Journal entry** — a compact block appended to a dated note (`YYYYMMDD.md`) in your journal notebook. Appears alongside any other content you write that day. Compatible with `nb daily` — both write to the same file.

**annn tasknote** — a freeform note file attached to a task by the [annn hook](https://github.com/linuxcaffe/tw-ann-hook), stored in `~/.task/notes/`. tw2nb transfers its contents to nb on task completion or deletion.

## Installation

### Option 1 — Install script

```bash
git clone https://github.com/linuxcaffe/tw2nb
bash tw2nb/tw2nb.install
```

Installs hooks to `~/.task/hooks/`, library and scripts to `~/.task/scripts/`, config to `~/.task/config/tw2nb.rc` (skipped if already present), and nb plugins to `~/.nb/.plugins/`.

### Option 2 — Via [awesome-taskwarrior](https://github.com/linuxcaffe/awesome-taskwarrior)

```bash
tw -I tw2nb
```

### Option 3 — Manual

```bash
# 1. Create nb notebook for task notes
nb notebooks add tasks

# 2. Copy hook and library files
cp on-add_tw2nb.py on-modify_tw2nb.py ~/.task/hooks/
chmod +x ~/.task/hooks/on-add_tw2nb.py ~/.task/hooks/on-modify_tw2nb.py
cp tw2nb_lib.py tw2nb-retro ~/.task/scripts/
chmod +x ~/.task/scripts/tw2nb-retro

# 3. Copy config (skip if upgrading — do not overwrite your settings)
cp tw2nb.rc ~/.task/config/

# 4. Install nb plugins
nb plugin install plugins/tw.nb-plugin      # nb info command
nb plugin install plugins/grep.nb-plugin    # nb g search command

# 5. Add config include to .taskrc
echo "include ~/.task/config/tw2nb.rc" >> ~/.taskrc

# 6. Verify
task diag | grep hooks
```

## Configuration

`~/.task/config/tw2nb.rc`:

```ini
tw2nb.notebook          = tasks   # nb notebook for per-task todos
tw2nb.journal           = home    # nb notebook for the running journal
tw2nb.on_delete         = no      # archive deleted tasks too (yes/no)
tw2nb.journal_annotated = no      # also write a journal entry on annotation events (yes/no)
tw2nb.sync              = no      # run 'nb sync' after each archive (yes/no)
tw2nb.project_notebooks = no      # route tasks to a per-project notebook (yes/no)
tw2nb.project_depth     = top     # top: 'tw.gtk'→'tw'  |  full: 'tw.gtk'→'tw-gtk'
tw2nb.delete_tasknote   = no      # delete annn note file after transfer (yes/no)
tw2nb.annotations_in    = note    # where annotation history goes: note or journal
tw2nb.tasknote_in       = note    # where annn note content goes: note or journal
```

**`project_notebooks`** — when `yes`, tasks are routed to a notebook derived from their Taskwarrior project rather than `tw2nb.notebook`. Tasks with no project fall back to `tw2nb.notebook`. Notebooks are created automatically if absent.

**`project_depth`** — controls how the notebook name is derived from the project. `top` uses only the first segment: `tw.gtk` and `tw.sanity` both go to notebook `tw`. `full` uses the complete path with dots replaced by hyphens: `tw.gtk` → notebook `tw-gtk`.

**`annotations_in`** / **`tasknote_in`** — redirect content to one destination only. Set to `journal` and the annotation history (or annn note content) is embedded in the journal entry on completion, rather than appended to the task note. Not both.

## Usage

**Completing and logging tasks**

```bash
task 42 done                   # archives to nb; adds 'nb: tasks:N' breadcrumb to task
task log "Fixed the login bug" # already done — archives immediately on add
```

**Archiving deleted tasks** (requires `tw2nb.on_delete = yes`)

```bash
task 17 delete                 # archives to nb journal before removal
```

**Viewing archived tasks**

```bash
nb tasks: list                 # all task notes
nb todos --closed              # completed task todos only
nb home: 3                     # a specific journal page
nb info tasks:45               # live TW info for the task in note 45
nb info home:3                 # TW info for every task referenced in a journal page
```

**Searching the archive**

```bash
nb g "#project/tw"             # all tasks in the tw project
nb g "#bug"                    # by tag
nb g "abc12345"                # by uuid8
nb g -C 4 "login bug"          # 4 lines of context around each match
nb g -l "abc12345"             # list matching notes only (no context)
```

**Backfilling past tasks**

```bash
tw2nb-retro --dry-run              # preview what would be archived
tw2nb-retro                        # archive all completed tasks
tw2nb-retro --from 2026-01-01      # only tasks completed since a date
tw2nb-retro --status all           # include deleted tasks too
tw2nb-retro -v                     # verbose: show each task as it is processed
```

## Example workflow

1. Complete a task that has annotations and an attached annn note:
   ```
   task 42 done
   ```

2. tw2nb archives it automatically:
   - A closed todo appears in your `tasks` notebook (or project notebook if configured).
   - Today's journal gets a `## ✅ Fixed the login bug` entry with tags, UUID, duration, and — depending on `annotations_in` / `tasknote_in` — annotation history and task note content.
   - The task receives a breadcrumb: `nb: tasks:42`.

3. Two weeks later, you browse that journal page and want to check a related task:
   ```
   nb info home:20260320
   ```
   `nb info` finds every uuid8 on the page and runs `task info` for each. Active tasks show their current state; tasks not found in Taskwarrior are flagged cleanly.

4. You search everything related to a project across all notebooks:
   ```
   nb g "#project/tw"
   ```

## Project status

⚠️ Early release. The hook is stable for daily use but the configuration surface and note format may change before 1.0.

## Further reading

- [nb](https://xwmx.github.io/nb/) — the note-taking tool tw2nb archives to
- [annn](https://github.com/linuxcaffe/tw-ann-hook) — annotation and task-note hook that tw2nb integrates with
- [awesome-taskwarrior](https://github.com/linuxcaffe/awesome-taskwarrior) — the ecosystem this lives in

## Metadata

- License: MIT
- Language: Python 3, Bash
- Requires: Taskwarrior 2.6.2, Python 3.6+, [nb](https://xwmx.github.io/nb/)
- Platforms: Linux
- Version: 0.1.0
