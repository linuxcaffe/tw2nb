"""tw2nb with nb tw tasknotes (tw-nb-interop M4): a task with its own tasknote isn't archived a
second time; the archive breadcrumb is a path selector; (the on-exit hook that mirrors status and fulfils nb: requests is the nbnotes app's since
tw2nb 1.5.0, tested in tw-nbnotes-hook)."""
import json
import re
import time


def done(task):
    t = dict(task, status='completed', end=time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
    return task, t


def journal_text(env):
    return '\n'.join(p.read_text() for p in (env.nb_dir / 'home').glob('*.md'))


def test_archive_breadcrumb_is_a_path_selector(env):
    uuid = env.add_task('--', 'No tasknote here')
    out = env.hook('on-modify_tw2nb.py', *done(env.export(uuid)))
    task = json.loads(out.stdout.strip().splitlines()[-1])
    crumbs = [a['description'] for a in task.get('annotations', []) if a['description'].startswith('nb: ')]
    assert len(crumbs) == 1
    assert re.fullmatch(r'nb: tasks:[^/\s]+\.md', crumbs[0]), crumbs[0]
    assert (env.nb_dir / 'tasks' / crumbs[0][len('nb: tasks:'):]).is_file()


def test_task_with_tasknote_is_not_archived_twice(env):
    uuid = env.add_task('--', 'Has its own note')
    note = env.tw_note(uuid)
    before = sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md'))
    out = env.hook('on-modify_tw2nb.py', *done(env.export(uuid)))
    task = json.loads(out.stdout.strip().splitlines()[-1])
    assert sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md')) == before, 'no archive todo'
    assert [a['description'] for a in task['annotations'] if a['description'].startswith('nb: ')] == \
        [f'nb: tasknotes:{note.name}'], 'no second breadcrumb'
    assert f'[[tasknotes:{note.name}]]' in journal_text(env)


def test_journal_links_the_archive_as_a_wikilink(env):
    uuid = env.add_task('--', 'Journal link')
    env.hook('on-modify_tw2nb.py', *done(env.export(uuid)))
    assert re.search(r'→ task note: \[\[tasks:[^\]/]+\.md\]\]', journal_text(env))










# ── nb: requests (tw-nb-interop M7 (b), djp 2026-11-02) ───────────────────────────────────
# A bare `nb:` (or `nb: <notebook>:`) annotation asks for a note; nbnotes' on-exit runs `nb tw note`,
# which makes it and swaps the request for the real link. From any client, nobody names it.

def anns(env, uuid):
    return [a['description'] for a in env.export(uuid).get('annotations', [])]








def test_on_modify_a_request_is_not_archived_as_an_annotation(env):
    uuid = env.add_task('--', 'Just asking')
    before = env.export(uuid)
    after = dict(before, annotations=[{'entry': '20261103T000000Z', 'description': 'nb:'}])
    tasks_before = sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md'))
    out = env.hook('on-modify_tw2nb.py', before, after)
    assert json.loads(out.stdout.strip().splitlines()[-1])['annotations'] == after['annotations']
    assert sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md')) == tasks_before
