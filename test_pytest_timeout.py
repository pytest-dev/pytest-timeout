import os
import os.path
import signal
import time

import pytest

pytest_plugins = 'pytester'

have_sigalrm = pytest.mark.skipif(not hasattr(signal, "SIGALRM"),
                                  reason='OS does not have SIGALRM')

@pytest.fixture
def testdir(testdir):
    if hasattr(testdir, "runpytest_subprocess"):
        # on pytest-2.8 runpytest runs inline by default
        # patch the testdir instance to use the subprocess method
        testdir.runpytest = testdir.runpytest_subprocess
    return testdir


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
        import time

        def test_foo():
            time.sleep(2)
    """)
    monkeypatch.setitem(os.environ, 'PYTEST_TIMEOUT', '1')
    result = testdir.runpytest()
    assert result.ret > 0


# @pytest.mark.parametrize('meth', [have_sigalrm('signal'), 'thread'])
# def test_func_fix(meth, testdir):
#     testdir.makepyfile("""
#         import time, pytest

#         @pytest.fixture(scope='function')
#         def fix():
#             time.sleep(2)

#         def test_foo(fix):
#             pass
#     """)
#     result = testdir.runpytest('--timeout=1',
#                                '--timeout_method={0}'.format(meth))
#     assert result.ret > 0
#     assert 'Timeout' in result.stdout.str() + result.stderr.str()


@pytest.mark.parametrize('meth', [have_sigalrm('signal'), 'thread'])
@pytest.mark.parametrize('scope', ['function', 'class', 'module', 'session'])
def test_fix_setup(meth, scope, testdir):
    testdir.makepyfile("""
        import time, pytest

        class TestFoo:

            @pytest.fixture(scope='{scope}')
            def fix(self):
                time.sleep(2)

            def test_foo(self, fix):
                pass
    """.format(scope=scope))
    result = testdir.runpytest('--timeout=1',
                               '--timeout_method={0}'.format(meth))
    assert result.ret > 0
    assert 'Timeout' in result.stdout.str() + result.stderr.str()


@pytest.mark.parametrize('meth', [have_sigalrm('signal'), 'thread'])
@pytest.mark.parametrize('scope', ['function', 'class', 'module', 'session'])
def test_fix_finalizer(meth, scope, testdir):
    testdir.makepyfile("""
        import time, pytest

        class TestFoo:

            @pytest.fixture(scope='{scope}')
            def fix(self, request):
                print('fix setup')
                def fin():
                    print('fix finaliser')
                    time.sleep(2)
                request.addfinalizer(fin)

            def test_foo(self, fix):
                pass
    """.format(scope=scope))
    result = testdir.runpytest('--timeout=1', '-s',
                               '--timeout_method={0}'.format(meth))
    assert result.ret > 0
    assert 'Timeout' in result.stdout.str() + result.stderr.str()


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


def test_suppresses_timeout_when_pdb_is_entered(testdir):
    p1 = testdir.makepyfile("""
        import pytest, pdb

        @pytest.mark.timeout(1)
        def test_foo():
            pdb.set_trace()
    """)
    child = testdir.spawn_pytest(str(p1))
    child.expect("test_foo")
    time.sleep(2)
    child.send('c\n')
    child.sendeof()
    result = child.read()
    if child.isalive():
        child.wait()
    assert b'Timeout >1s' not in result
