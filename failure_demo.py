"""Demonstration of timeout failures using pytest_timeout.

To use this demo, invoke pytest on it::

   pytest failure_demo.py
"""
import threading
import time

import pytest


def sleep(s):
    """Sleep for a while, possibly triggering a timeout.

    Also adds another function on the stack showing off the stack.
    """
    # Separate function to demonstrate nested calls
    time.sleep(s)


@pytest.mark.timeout(1)
def test_simple():
    """Basic timeout demonstration."""
    sleep(2)


def _run():
    sleep(2)


@pytest.mark.timeout(1)
def test_thread():
    """Timeout when multiple threads are running."""
    t = threading.Thread(target=_run)
    t.start()
    sleep(2)
