import os
import os.path
import signal
import threading

import pytest


pytest_plugins = 'pytester'


# This is required since our tests run py.test in a temporary
# directory and that py.test process needs to find the pytest_timeout
# module on it's sys.path.
os.environ['PYTHONPATH'] = os.path.dirname(__file__)


have_sigalrm = pytest.mark.skipif('not hasattr(signal, "SIGALRM")')


@have_sigalrm
def test_sigalrm(testdir):
    # This inserts "-p pytest_timeout" to the py.test argument list.
    # This must be availabe before the --timeout parameter can be
    # used.  The alternative is to use pytest_plugins in conftest.py.
    testdir.plugins.append('pytest_timeout')
    testdir.makepyfile("""
        import time

        def test_foo():
            time.sleep(2)
     """)
    result = testdir.runpytest('--timeout=1')
    result.stdout.fnmatch_lines([
            '*Failed: Timeout >1s*'
            ])


# def test_thread():
#     t = threading.Thread(target=time.sleep, args=(10,))
#     t.daemon = True
#     t.start()
#     print 'foo'
#     time.sleep(10)
#     print 'bar'
#     assert False
