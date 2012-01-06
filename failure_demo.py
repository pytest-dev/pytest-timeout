"""Demonstration of timeout failures using pytest_timeout

To use this demo, invoke as::

   py.test -p pytest_timeout --timeout=1 failure_demo.py

since with the default timeout the tests will pass.
"""

import signal
import time

import pytest


pytest_plugins = 'pytest_timeout'


have_sigalrm = pytest.mark.skipif('not hasattr(signal, "SIGALRM")')


@have_sigalrm
def test_sigalrm():
    time.sleep(2)
