"""tw2nb 1.4.1: tw2nb.rc is discrete (CONVENTIONS §7): its hooks read it, so it has no include,
and installing takes out one an older version (or a hand repair) left in .taskrc or included.rc.

1.4.0 stopped adding the include but left any existing one in place; on 2026-11-04 one in
included.rc was re-enabled by hand. Runs the real installer in a throwaway HOME."""
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run(home, action):
    env = {'PATH': os.environ['PATH'], 'HOME': str(home)}
    r = subprocess.run(['bash', str(REPO / 'tw2nb.install'), action], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


@pytest.fixture
def home(tmp_path):
    h = tmp_path / 'home'
    (h / '.task' / 'config').mkdir(parents=True)
    (h / '.task' / 'hooks').mkdir()
    (h / '.task' / 'scripts').mkdir()
    return h


@pytest.mark.parametrize('line', ['include ~/.task/config/tw2nb.rc',
                                  '#include ~/.task/config/tw2nb.rc   # tw -r tw2nb 2026-10-31: file missing'])
def test_install_takes_an_old_include_out(home, line):
    inc = home / '.task' / 'config' / 'included.rc'
    inc.write_text(f'include ~/.task/config/other.rc\n{line}\ninclude ~/.task/config/old-tw2nb.rc\n')
    (home / '.taskrc').write_text(f'include ~/.task/config/included.rc\n{line}\n')
    out = run(home, 'install')
    assert 'config/tw2nb.rc' not in inc.read_text() + (home / '.taskrc').read_text()
    assert 'other.rc' in inc.read_text() and 'old-tw2nb.rc' in inc.read_text()
    assert 'included.rc' in (home / '.taskrc').read_text()
    assert 'reads its own settings' in out


def test_install_without_an_include_adds_none(home):
    (home / '.taskrc').write_text('include ~/.task/config/included.rc\n')
    run(home, 'install')
    assert 'tw2nb.rc' not in (home / '.taskrc').read_text()
    assert (home / '.task' / 'config' / 'tw2nb.rc').is_file()


def test_remove_drops_an_include_from_either_file(home):
    run(home, 'install')
    inc = home / '.task' / 'config' / 'included.rc'
    inc.write_text('include ~/.task/config/tw2nb.rc\ninclude ~/.task/config/old-tw2nb.rc\n')
    run(home, 'remove')
    assert 'config/tw2nb.rc' not in inc.read_text()
    assert 'old-tw2nb.rc' in inc.read_text()


def test_installs_from_only_the_files_tw_downloads(tmp_path):
    """1.4.3: `tw -u` stages only the .meta's files=, so plugins/ isn't there. The installer copied
    plugins/grep.nb-plugin whenever nb was here and grep wasn't, and set -e failed the whole update
    (the phone, 2026-11-04). tw2nb doesn't use grep; nb-plugins owns it. Nothing outside files=."""
    import re, shutil
    stage = tmp_path / 'stage'
    stage.mkdir()
    files = re.search(r'^files=(.*)$', (REPO / 'tw2nb.meta').read_text(), re.M).group(1).split(',')
    for entry in files:
        name = entry.split(':')[0]
        shutil.copy(REPO / name, stage / name)
    shutil.copy(REPO / 'tw2nb.install', stage / 'tw2nb.install')
    home = tmp_path / 'home'
    for d in ('config', 'hooks', 'scripts'):
        (home / '.task' / d).mkdir(parents=True)
    (home / '.nb' / '.plugins').mkdir(parents=True)          # nb's plugins folder, no grep in it
    bin_ = tmp_path / 'bin'
    bin_.mkdir()
    (bin_ / 'nb').write_text('#!/bin/sh\n')
    (bin_ / 'nb').chmod(0o755)
    env = {'PATH': f"{bin_}:{os.environ['PATH']}", 'HOME': str(home)}
    r = subprocess.run(['bash', str(stage / 'tw2nb.install'), 'install'], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (home / '.nb' / '.plugins' / 'grep.nb-plugin').exists()
    assert 'nb plugins install' not in r.stdout   # 1.5.1: tw2nb needs no nb-plugin, so names none


def test_1_5_takes_out_the_old_on_exit_and_names_nbnotes(home):
    """1.5.0: making and updating task notes moved to the nbnotes app (tw-nbnotes-hook), so the phone
    can have them without tw2nb's archive and journal. An update takes out on-exit_tw2nb.py (two
    copies would run nb tw twice) and, without nbnotes, says how to get it."""
    hooks = home / '.task' / 'hooks'
    (hooks / 'on-exit_tw2nb.py').write_text('# 1.4\n')
    out = run(home, 'install')
    assert not (hooks / 'on-exit_tw2nb.py').exists()
    assert (hooks / 'on-modify_tw2nb.py').exists()
    assert 'tw -I nbnotes' in out
    assert 'on-exit_tw2nb' not in (home / '.task' / 'config' / '.tw_manifest').read_text()
    (hooks / 'on-exit_nbnotes.py').write_text('# nbnotes\n')
    assert 'tw -I nbnotes' not in run(home, 'install')
