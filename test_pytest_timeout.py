import os.path
import signal
import sys
import time

import pexpect
import pytest
from pytest_timeout import PYTEST_FAILURE_MESSAGE


MATCH_FAILURE_MESSAGE = f"*Failed: {PYTEST_FAILURE_MESSAGE}*"
pytest_plugins = "pytester"

have_sigalrm = pytest.mark.skipif(
    not hasattr(signal, "SIGALRM"), reason="OS does not have SIGALRM"
)
have_spawn = pytest.mark.skipif(
    not hasattr(pexpect, "spawn"), reason="pexpect does not have spawn"
)


def test_header(pytester):
    pytester.makepyfile(
        """
        def test_x(): pass
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1", "--session-timeout=2")
    result.stdout.fnmatch_lines(
        [
            "timeout: 1.0s",
            "timeout method:*",
            "timeout func_only:*",
            "session timeout: 2.0s",
        ]
    )


@have_sigalrm
def test_sigalrm(pytester):
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
     """
    )
    result = pytester.runpytest_subprocess("--timeout=1")
    result.stdout.fnmatch_lines([MATCH_FAILURE_MESSAGE % "1.0"])


def test_thread(pytester):
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1", "--timeout-method=thread")
    result.stdout.fnmatch_lines(
        [
            "*++ Timeout ++*",
            "*~~ Stack of MainThread* ~~*",
            "*File *, line *, in *",
            "*++ Timeout ++*",
        ]
    )
    assert "++ Timeout ++" in result.stdout.lines[-1]


@pytest.mark.skipif(
    hasattr(sys, "pypy_version_info"), reason="pypy coverage seems broken currently"
)
def test_cov(pytester):
    # This test requires pytest-cov
    pytest.importorskip("pytest_cov")
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
    """
    )
    result = pytester.runpytest_subprocess(
        "--timeout=1", "--cov=test_cov", "--timeout-method=thread"
    )
    result.stdout.fnmatch_lines(
        [
            "*++ Timeout ++*",
            "*~~ Stack of MainThread* ~~*",
            "*File *, line *, in *",
            "*++ Timeout ++*",
        ]
    )
    assert "++ Timeout ++" in result.stdout.lines[-1]


def test_timeout_env(pytester, monkeypatch):
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
    """
    )
    monkeypatch.setitem(os.environ, "PYTEST_TIMEOUT", "1")
    result = pytester.runpytest_subprocess()
    assert result.ret > 0


# @pytest.mark.parametrize('meth', [have_sigalrm('signal'), 'thread'])
# def test_func_fix(meth, pytester):
#     pytester.makepyfile("""
#         import time, pytest

#         @pytest.fixture(scope='function')
#         def fix():
#             time.sleep(2)

#         def test_foo(fix):
#             pass
#     """)
#     result = pytester.runpytest_subprocess('--timeout=1',
#                                '--timeout-method={0}'.format(meth))
#     assert result.ret > 0
#     assert 'Timeout' in result.stdout.str() + result.stderr.str()


@pytest.mark.parametrize("meth", [pytest.param("signal", marks=have_sigalrm), "thread"])
@pytest.mark.parametrize("scope", ["function", "class", "module", "session"])
def test_fix_setup(meth, scope, pytester):
    pytester.makepyfile(
        """
        import time, pytest

        class TestFoo:

            @pytest.fixture(scope='{scope}')
            def fix(self):
                time.sleep(2)

            def test_foo(self, fix):
                pass
    """.format(
            scope=scope
        )
    )
    result = pytester.runpytest_subprocess("--timeout=1", f"--timeout-method={meth}")
    assert result.ret > 0
    assert "Timeout" in result.stdout.str() + result.stderr.str()


def test_fix_setup_func_only(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        class TestFoo:

            @pytest.fixture
            def fix(self):
                time.sleep(0.1)

            @pytest.mark.timeout(func_only=True)
            def test_foo(self, fix):
                pass
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1")
    assert result.ret == 0
    assert "Timeout" not in result.stdout.str() + result.stderr.str()


@pytest.mark.parametrize("meth", [pytest.param("signal", marks=have_sigalrm), "thread"])
@pytest.mark.parametrize("scope", ["function", "class", "module", "session"])
def test_fix_finalizer(meth, scope, pytester):
    pytester.makepyfile(
        """
        import time, pytest

        class TestFoo:

            @pytest.fixture
            def fix(self, request):
                print('fix setup')
                def fin():
                    print('fix finaliser')
                    time.sleep(2)
                request.addfinalizer(fin)

            def test_foo(self, fix):
                pass
    """
    )
    result = pytester.runpytest_subprocess(
        "--timeout=1", "-s", f"--timeout-method={meth}"
    )
    assert result.ret > 0
    assert "Timeout" in result.stdout.str() + result.stderr.str()


def test_fix_finalizer_func_only(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        class TestFoo:

            @pytest.fixture
            def fix(self, request):
                print('fix setup')
                def fin():
                    print('fix finaliser')
                    time.sleep(0.1)
                request.addfinalizer(fin)

            @pytest.mark.timeout(func_only=True)
            def test_foo(self, fix):
                pass
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1", "-s")
    assert result.ret == 0
    assert "Timeout" not in result.stdout.str() + result.stderr.str()


@have_sigalrm
def test_timeout_mark_sigalrm(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
            assert False
    """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines([MATCH_FAILURE_MESSAGE % "1.0"])


def test_timeout_mark_timer(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.mark.timeout(1)
        def test_foo():
            time.sleep(2)
    """
    )
    result = pytester.runpytest_subprocess("--timeout-method=thread")
    result.stdout.fnmatch_lines(["*++ Timeout ++*"])


def test_timeout_mark_non_int(pytester):
    pytester.makepyfile(
        """
     import time, pytest

     @pytest.mark.timeout(0.01)
     def test_foo():
         time.sleep(1)
    """
    )
    result = pytester.runpytest_subprocess("--timeout-method=thread")
    result.stdout.fnmatch_lines(["*++ Timeout ++*"])


def test_timeout_mark_non_number(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.timeout('foo')
        def test_foo():
            pass
   """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines(["*ValueError*"])


def test_timeout_mark_args(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.timeout(1, 2)
        def test_foo():
            pass
    """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines(["*ValueError*"])


def test_timeout_mark_method_nokw(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.mark.timeout(1, 'thread')
        def test_foo():
            time.sleep(2)
    """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines(["*+ Timeout +*"])


def test_timeout_mark_noargs(pytester):
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.timeout
        def test_foo():
            pass
    """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines(["*TypeError*"])


def test_ini_timeout(pytester):
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
    """
    )
    pytester.makeini(
        """
        [pytest]
        timeout = 1
    """
    )
    result = pytester.runpytest_subprocess()
    assert result.ret


def test_ini_timeout_func_only(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.fixture
        def slow():
            time.sleep(2)
        def test_foo(slow):
            pass
    """
    )
    pytester.makeini(
        """
        [pytest]
        timeout = 1
        timeout_func_only = true
    """
    )
    result = pytester.runpytest_subprocess()
    assert result.ret == 0


def test_ini_timeout_func_only_marker_override(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.fixture
        def slow():
            time.sleep(2)
        @pytest.mark.timeout(1.5)
        def test_foo(slow):
            pass
    """
    )
    pytester.makeini(
        """
        [pytest]
        timeout = 1
        timeout_func_only = true
    """
    )
    result = pytester.runpytest_subprocess()
    assert result.ret == 0


def test_ini_method(pytester):
    pytester.makepyfile(
        """
        import time

        def test_foo():
            time.sleep(2)
    """
    )
    pytester.makeini(
        """
        [pytest]
        timeout = 1
        timeout_method = thread
    """
    )
    result = pytester.runpytest_subprocess()
    assert "=== 1 failed in " not in result.outlines[-1]


def test_timeout_marker_inheritance(pytester):
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.mark.timeout(timeout=2)
        class TestFoo:

            @pytest.mark.timeout(timeout=3)
            def test_foo_2(self):
                time.sleep(2)

            def test_foo_1(self):
                time.sleep(1)
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1", "-s")
    assert result.ret == 0
    assert "Timeout" not in result.stdout.str() + result.stderr.str()


def test_marker_help(pytester):
    result = pytester.runpytest_subprocess("--markers")
    result.stdout.fnmatch_lines(["@pytest.mark.timeout(*"])


@pytest.mark.parametrize(
    ["debugging_module", "debugging_set_trace"],
    [
        ("pdb", "set_trace()"),
        pytest.param(
            "ipdb",
            "set_trace()",
            marks=pytest.mark.xfail(
                reason="waiting on https://github.com/pytest-dev/pytest/pull/7207"
                " to allow proper testing"
            ),
        ),
        pytest.param(
            "pydevd",
            "settrace(port=4678)",
            marks=pytest.mark.xfail(reason="in need of way to setup pydevd server"),
        ),
    ],
)
@have_spawn
def test_suppresses_timeout_when_debugger_is_entered(
    pytester, debugging_module, debugging_set_trace
):
    p1 = pytester.makepyfile(
        """
        import pytest, {debugging_module}

        @pytest.mark.timeout(1)
        def test_foo():
            {debugging_module}.{debugging_set_trace}
    """.format(
            debugging_module=debugging_module, debugging_set_trace=debugging_set_trace
        )
    )
    child = pytester.spawn_pytest(str(p1))
    child.expect("test_foo")
    time.sleep(0.2)
    child.send("c\n")
    child.sendeof()
    result = child.read().decode().lower()
    if child.isalive():
        child.terminate(force=True)
    assert "timeout (>1.0s)" not in result
    assert "fail" not in result


@pytest.mark.parametrize(
    ["debugging_module", "debugging_set_trace"],
    [
        ("pdb", "set_trace()"),
        pytest.param(
            "ipdb",
            "set_trace()",
            marks=pytest.mark.xfail(
                reason="waiting on https://github.com/pytest-dev/pytest/pull/7207"
                " to allow proper testing"
            ),
        ),
        pytest.param(
            "pydevd",
            "settrace(port=4678)",
            marks=pytest.mark.xfail(reason="in need of way to setup pydevd server"),
        ),
    ],
)
@have_spawn
def test_disable_debugger_detection_flag(
    pytester, debugging_module, debugging_set_trace
):
    p1 = pytester.makepyfile(
        """
        import pytest, {debugging_module}

        @pytest.mark.timeout(1)
        def test_foo():
            {debugging_module}.{debugging_set_trace}
    """.format(
            debugging_module=debugging_module, debugging_set_trace=debugging_set_trace
        )
    )
    child = pytester.spawn_pytest(f"{p1} --timeout-disable-debugger-detection")
    child.expect("test_foo")
    time.sleep(1.2)
    result = child.read().decode().lower()
    if child.isalive():
        child.terminate(force=True)
    assert "timeout (>1.0s)" in result
    assert "fail" in result


def test_is_debugging(monkeypatch):
    import pytest_timeout

    assert not pytest_timeout.is_debugging()

    # create a fake module named "custom.pydevd" with a trace function on it
    from types import ModuleType

    module_name = "custom.pydevd"
    module = ModuleType(module_name)
    monkeypatch.setitem(sys.modules, module_name, module)

    def custom_trace(*args):
        pass

    custom_trace.__module__ = module_name
    module.custom_trace = custom_trace

    assert pytest_timeout.is_debugging(custom_trace)


def test_not_main_thread(pytester):
    pytest.skip("The 'pytest_timeout.timeout_setup' function no longer exists")
    pytester.makepyfile(
        """
        import threading
        import pytest_timeout

        current_timeout_setup = pytest_timeout.timeout_setup

        def new_timeout_setup(item):
            threading.Thread(
                target=current_timeout_setup, args=(item),
            ).join()

        pytest_timeout.timeout_setup = new_timeout_setup

        def test_x(): pass
    """
    )
    result = pytester.runpytest_subprocess("--timeout=1")
    result.stdout.fnmatch_lines(
        ["timeout: 1.0s", "timeout method:*", "timeout func_only:*"]
    )


def test_plugin_interface(pytester):
    pytester.makeconftest(
        """
     import pytest

     @pytest.mark.tryfirst
     def pytest_timeout_set_timer(item, settings):
         print()
         print("pytest_timeout_set_timer")
         return True

     @pytest.mark.tryfirst
     def pytest_timeout_cancel_timer(item):
         print()
         print("pytest_timeout_cancel_timer")
         return True
    """
    )
    pytester.makepyfile(
        """
     import pytest

     @pytest.mark.timeout(1)
     def test_foo():
         pass
    """
    )
    result = pytester.runpytest_subprocess("-s")
    result.stdout.fnmatch_lines(
        [
            "pytest_timeout_set_timer",
            "pytest_timeout_cancel_timer",
        ]
    )


def test_session_timeout(pytester):
    # This is designed to timeout during hte first test to ensure 
    # - the first test still runs to completion
    # - the second test is not started 
    pytester.makepyfile(
        """
        import time, pytest

        @pytest.fixture()
        def slow_setup_and_teardown():
            time.sleep(1)
            yield
            time.sleep(1)

        def test_one(slow_setup_and_teardown):
            time.sleep(1)

        def test_two(slow_setup_and_teardown):
            time.sleep(1)
        """
    )
    result = pytester.runpytest_subprocess("--session-timeout", "2")
    result.stdout.fnmatch_lines(["*!! session-timeout: 2.0 sec exceeded !!!*"])
    # This would be 2 passed if the second test was allowed to run
    result.assert_outcomes(passed=1)  


def test_ini_session_timeout(pytester):
    pytester.makepyfile(
        """
        import time

        def test_one():
            time.sleep(2)

        def test_two():
            time.sleep(2)
        """
    )
    pytester.makeini(
        """
        [pytest]
        session_timeout = 1
        """
    )
    result = pytester.runpytest_subprocess()
    result.stdout.fnmatch_lines(["*!! session-timeout: 1.0 sec exceeded !!!*"])
    result.assert_outcomes(passed=1)
