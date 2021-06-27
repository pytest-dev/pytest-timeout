#!/usr/bin/env python3
"""Define pytest hooks as part of the pytest-timeout test suite."""
import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    """Create a conftest.py file.

    This should be considered a test, not a fixture!
    By creating a conftest.py file before actually running the test,
    it can be tested/ensured that the functionality implemented in
    #90 works reliably.
    With untypical test, all other tests are employed to ensure correct
    behaviour in terms of #90 apart from their designated checks.

    The implementation is inspired by ``_pytest.python.pytest_pyfunc_call``:
    https://github.com/pytest-dev/pytest/blob/
      f28421cc7068b13ba63c1f60cc21f898cccea36c/src/_pytest/python.py#L179
    """
    testdir = item.funcargs.get("testdir", None)
    if hasattr(testdir, "makepyfile"):
        testdir.makepyfile(
            conftest="""
            import pytest

            @pytest.hookimpl(hookwrapper=True)
            def pytest_runtest_makereport(item, call):
                r = yield
                if not hasattr(r, "get_result"):
                    return
                report = r.get_result()
                timed_out = False
                if hasattr(call.excinfo, "value"):
                    msg = getattr(call.excinfo.value, "msg", None)
                    if isinstance(msg, str) and msg.startswith("Timeout >"):
                        timed_out = True
                ref_timed_out = bool(getattr(report, "timed_out", None))
                assert ref_timed_out == timed_out, "#90 customisation broken!"
        """
        )
    yield
