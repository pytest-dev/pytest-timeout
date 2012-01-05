import signal
import threading

import pytest


pytest_plugins = 'pytester', 'timeout'


have_sigalrm = pytest.mark.skipif('not hasattr(signal, "SIGALRM")')


@have_sigalrm
def test_sigalrm(testdir):
    testdir.makepyfile("""
        import time

        pytest_plugins = 'timeout'

        def test_foo():
            time.sleep(2)
     """)
    result = testdir.runpytest('--timeout=1')
    result.stdout.fnmatch_lines([
            '*AssertionError*Timeout >1*'
            ])


# def test_thread():
#     t = threading.Thread(target=time.sleep, args=(10,))
#     t.daemon = True
#     t.start()
#     print 'foo'
#     time.sleep(10)
#     print 'bar'
#     assert False
