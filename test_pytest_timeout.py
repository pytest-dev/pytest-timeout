import os
import os.path
import signal

import pytest


pytest_plugins = 'pytester'


have_sigalrm = pytest.mark.skipif(not hasattr(signal, "SIGALRM"),
                                  reason='OS does not have SIGALRM')


@have_sigalrm
def test_sigalrm(testdir):
    testdir.makepyfile("""
        import time

        def test_foo():
            time.sleep(2)
     """)
    result = testdir.runpytest('--timeout=1')
    result.stdout.fnmatch_lines([
        '*Failed: Timeout >1s*'
    ])


def test_thread(testdir):
    testdir.makepyfile("""
        import time

        def test_foo():
            time.sleep(2)
    """)
    result = testdir.runpytest('--timeout=1', '--timeout_method=thread')
    result.stderr.fnmatch_lines([
        '*++ Timeout ++*',
        '*~~ Stack of MainThread* ~~*',
        '*File *, line *, in *',
        '*++ Timeout ++*',
    ])
    assert '++ Timeout ++' in result.stderr.lines[-1]


def test_timeout_env(testdir, monkeypatch):
    testdir.makepyfile("""
        import time, pytest

        def test_foo():
            time.sleep(2)
    """)
    monkeypatch.setitem(os.environ, 'PYTEST_TIMEOUT', '1')
    result = testdir.runpytest()
    assert result.ret > 0


@have_sigalrm
def test_timeout_mark_sigalrm(testdir):
    testdir.makepyfile("""
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
            assert False
    """)
    result = testdir.runpytest()
    result.stdout.fnmatch_lines(['*Failed: Timeout >1s*'])


def test_timeout_mark_timer(testdir):
    testdir.makepyfile("""
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
    """)
    result = testdir.runpytest('--timeout_method=thread')
    result.stderr.fnmatch_lines(['*++ Timeout ++*'])


def test_timeout_mark_nonint(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout('foo')
        def test_foo():
            pass
   """)
    result = testdir.runpytest()
    result.stdout.fnmatch_lines(['*ValueError*'])


def test_timeout_mark_args(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout(1, 2)
        def test_foo():
            pass
    """)
    result = testdir.runpytest()
    result.stdout.fnmatch_lines(['*ValueError*'])


def test_timeout_mark_method_nokw(testdir):
    testdir.makepyfile("""
        import time, pytest

        @pytest.mark.timeout(1, 'thread')
        def test_foo():
            time.sleep(2)
    """)
    result = testdir.runpytest()
    result.stderr.fnmatch_lines(['*+ Timeout +*'])


def test_timeout_mark_noargs(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout
        def test_foo():
            pass
    """)
    result = testdir.runpytest()
    result.stdout.fnmatch_lines(['*TypeError*'])


def test_ini_timeout(testdir):
    testdir.makepyfile("""
        import time

        def test_foo():
            time.sleep(2)
    """)
    testdir.makeini("""
        [pytest]
        timeout = 1
    """)
    result = testdir.runpytest()
    assert result.ret


def test_ini_method(testdir):
    testdir.makepyfile("""
        import time

        def test_foo():
            time.sleep(2)
    """)
    testdir.makeini("""
        [pytest]
        timeout = 1
        timeout_method = thread
    """)
    result = testdir.runpytest()
    assert '=== 1 failed in ' not in result.outlines[-1]


def test_marker_help(testdir):
    result = testdir.runpytest('--markers')
    result.stdout.fnmatch_lines(['@pytest.mark.timeout(*'])
