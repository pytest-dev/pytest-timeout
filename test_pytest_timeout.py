import os
import os.path
import signal
import threading

import pkg_resources
import pytest


pytest_plugins = 'pytester'


def pytest_funcarg__testdir(request):
    """Horible hack around setuptools' behaviour

    The simple solution would be to require to be installed
    (setuptools' develop mode would suffice).  However to make the
    test also run from a plain checkout we need to ensure the plugin
    is loaded by ensuring it is on sys.path and adding -p to the
    pytest commandline.  But we also want to run the tests without
    being installed but with an .egg-info directory present in the
    checkout.  In this scenario adding this directory on sys.path will
    make the entrypoint show up so we should no longer add -p to
    py.test.
    """
    testdir = request.getfuncargvalue('testdir')

    def run_entrypoing_test():
        test_script = testdir.makepyfile(entrypoint_check="""
            import sys, pkg_resources
            if 'timeout' in [ep.name for ep in
                             pkg_resources.iter_entry_points('pytest11')]:
                sys.exit(1)
            """)
        return testdir.runpython(test_script)

    runresult = request.cached_setup(setup=run_entrypoing_test)
    if not runresult.ret:
        os.environ['PYTHONPATH'] = os.path.dirname(__file__)
        if not os.path.isdir(os.path.join(os.path.dirname(__file__),
                                          'pytest_timeout.egg-info')):
            testdir.plugins.append('pytest_timeout')
    return testdir


have_sigalrm = pytest.mark.skipif('not hasattr(signal, "SIGALRM")')


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


@have_sigalrm
def test_timeout_mark_sigalrm(testdir):
    testdir.makepyfile("""
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
            assert False
    """)
    result = testdir.runpytest('--timeout=0')
    result.stdout.fnmatch_lines(['*Failed: Timeout >1s*'])


def test_timeout_mark_timer(testdir):
    testdir.makepyfile("""
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
    """)
    result = testdir.runpytest('--timeout=0', '--timeout_method=thread')
    result.stderr.fnmatch_lines(['*++ Timeout ++*'])


def test_timeout_mark_nonint(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout('foo')
        def test_foo():
            pass
   """)
    result = testdir.runpytest('--timeout=0')
    result.stdout.fnmatch_lines(['*ValueError*'])


def test_timeout_mark_args(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout(1, 2)
        def test_foo():
            pass
    """)
    result = testdir.runpytest('--timeout=0')
    result.stdout.fnmatch_lines(['*TypeError*'])


def test_timeout_mark_noargs(testdir):
    testdir.makepyfile("""
        import pytest

        @pytest.mark.timeout
        def test_foo():
            pass
    """)
    result = testdir.runpytest('--timeout=0')
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
