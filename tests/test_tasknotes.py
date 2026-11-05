"""tw2nb with nb tw tasknotes (tw-nb-interop M4): a task with its own tasknote isn't archived a
second time; the archive breadcrumb is a path selector; on-exit mirrors status via nb tw status."""
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


def test_on_exit_mirrors_status_into_the_tasknote(env):
    uuid = env.add_task('--', 'Mirror me')
    note = env.tw_note(uuid)
    env.task(uuid, 'done')
    env.hook('on-exit_tw2nb.py', env.export(uuid))
    assert 'tw_status: completed' in note.read_text()
    assert env.git_clean('tasknotes')


def test_on_exit_skips_tasks_without_a_path_link(env):
    uuid = env.add_task('--', 'Archive link only')
    env.task(uuid, 'annotate', '--', 'nb: tasks:3')
    r = env.hook('on-exit_tw2nb.py', env.export(uuid), {'not': 'a task'})
    assert r.returncode == 0 and r.stdout == ''


def test_on_exit_without_the_plugin_changes_nothing_but_says_so(plain):
    """1.4.2 (M7: never fail silently; djp 2026-11-04: a missing nb-plugin of ours names its
    install): nb is here, the plugin isn't, and a task links a note: one line says what's missing
    and the command. The phone's synced hooks did nothing, silently, until mobilize 0.10.1."""
    uuid = plain.add_task('--', 'No plugin')
    plain.task(uuid, 'annotate', '--', 'nb: tasknotes:x.note.md')
    r = plain.hook('on-exit_tw2nb.py', plain.export(uuid))
    assert r.returncode == 0
    out = r.stdout + r.stderr
    assert "nb-plugin tw is required" in out
    assert 'nb plugins install https://raw.githubusercontent.com/linuxcaffe/nb-plugins/main/tw.nb-plugin' in out
    assert out.count('nb-plugin tw') == 1


def test_on_exit_without_the_plugin_is_quiet_when_nothing_needs_it(plain):
    uuid = plain.add_task('--', 'No note at all')
    r = plain.hook('on-exit_tw2nb.py', plain.export(uuid))
    assert r.returncode == 0 and 'nb-plugin' not in r.stdout + r.stderr


# ── nb: requests (tw-nb-interop M7 (b), djp 2026-11-02) ───────────────────────────────────
# A bare `nb:` (or `nb: <notebook>:`) annotation asks for a note; on-exit runs `nb tw note`,
# which makes it and swaps the request for the real link. From any client, nobody names it.

def anns(env, uuid):
    return [a['description'] for a in env.export(uuid).get('annotations', [])]


def test_on_exit_fulfils_a_bare_request(env):
    uuid = env.add_task('--', 'Order the tiles')
    env.task(uuid, 'annotate', '--', 'nb:')
    r = env.hook('on-exit_tw2nb.py', env.export(uuid))
    assert r.returncode == 0, r.stderr
    notes = list((env.nb_dir / 'tasknotes').glob(f'*{uuid[:8]}.note.md'))
    assert len(notes) == 1
    assert anns(env, uuid) == [f'nb: tasknotes:{notes[0].name}']


def test_on_exit_fulfils_a_request_for_another_notebook(env):
    env.run('nb', 'notebooks', 'add', 'acme')
    uuid = env.add_task('--', 'Call Jones')
    env.task(uuid, 'annotate', '--', 'nb: acme:')
    env.hook('on-exit_tw2nb.py', env.export(uuid))
    notes = list((env.nb_dir / 'acme').glob(f'*{uuid[:8]}.note.md'))
    assert len(notes) == 1
    assert anns(env, uuid) == [f'nb: acme:{notes[0].name}']


def test_on_exit_request_for_a_missing_notebook_never_fails_the_command(env):
    uuid = env.add_task('--', 'Nowhere')
    env.task(uuid, 'annotate', '--', 'nb: nosuch:')
    r = env.hook('on-exit_tw2nb.py', env.export(uuid))
    assert r.returncode == 0
    assert 'nosuch' in r.stderr
    assert anns(env, uuid) == ['nb: nosuch:']


def test_on_modify_a_request_is_not_archived_as_an_annotation(env):
    uuid = env.add_task('--', 'Just asking')
    before = env.export(uuid)
    after = dict(before, annotations=[{'entry': '20261103T000000Z', 'description': 'nb:'}])
    tasks_before = sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md'))
    out = env.hook('on-modify_tw2nb.py', before, after)
    assert json.loads(out.stdout.strip().splitlines()[-1])['annotations'] == after['annotations']
    assert sorted(p.name for p in (env.nb_dir / 'tasks').glob('*.md')) == tasks_before
