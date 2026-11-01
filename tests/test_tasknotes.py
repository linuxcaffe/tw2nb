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


def test_on_exit_without_the_plugin_does_nothing(plain):
    uuid = plain.add_task('--', 'No plugin')
    plain.task(uuid, 'annotate', '--', 'nb: tasknotes:x.note.md')
    r = plain.hook('on-exit_tw2nb.py', plain.export(uuid))
    assert r.returncode == 0
