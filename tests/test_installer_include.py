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
