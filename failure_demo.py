"""Demonstration of timeout failures using pytest_timeout

To use this demo, invoke py.test on it::

   py.test failure_demo.py
"""

import threading
import time

import pytest


def sleep(s):
    # Separate function to demonstrate nested calls
    time.sleep(s)


@pytest.mark.timeout(1)
def test_simple():
    sleep(2)


def run():
    sleep(2)


@pytest.mark.timeout(1)
def test_thread():
    t = threading.Thread(target=run)
    t.start()
    sleep(2)
