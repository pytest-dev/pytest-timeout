"""Timeout for tests to stop hanging testruns

This plugin will dump the stack and terminate the test.  This can be
useful when running tests on a continuous integration server.

If the platform supports SIGALRM this is used to raise an exception in
the test, otherwise os._exit(1) is used.
"""

import os
import signal
import sys
import threading
import traceback


SIGALRM = getattr(signal, 'SIGALRM', None)


def pytest_addoption(parser):
    """Add options to control the faulthandler and it's timeout"""
    group = parser.getgroup('timeout', 'Dump stacks after timeout')
    group.addoption('--timeout',
                    type=int,
                    default=300,
                    help='Timeout before dumping the traceback [300]')


def pytest_configure(config):
    """Activate faulthandler plugin if appropriate"""
    if config.getvalue('timeout') > 0:
        config.pluginmanager.register(FaultHandlerPlugin(config), 'timeout')


class FaultHandlerPlugin(object):
    """The timeout plugin"""

    def __init__(self, config):
        self.timeout = config.getvalue('timeout')
        if not SIGALRM:
            self._current_timer = None

    def pytest_runtest_setup(self, item):
        """Setup up a timeout trigger and handler"""
        if SIGALRM:

            def handler(signum, frame):
                self.timeout_sigalrm(item, frame)

            signal.signal(signal.SIGALRM, handler)
            signal.alarm(self.timeout)

        else:
            timer = threading.Timer(self.timeout, self.timeout_thread, (item,))
            self._current_timer = timer
            timer.start()


    def pytest_runtest_teardown(self):
        """Cancel the timeout trigger"""
        if SIGALRM:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        else:
            self._current_timer.cancel()

    def timeout_sigalrm(self, item, frame=None):
        """Dump stack of threads and raise an exception

        This will output the stacks of any threads other then the
        current to stderr and then raise an AssertionError, thus
        terminating the test.
        """
        sep = '\n' + '+' * 10 + ' timeout ' + '+' * 10 + '\n'
        nthreads = len(threading.enumerate())
        if nthreads > 1:
            sys.stderr.write(sep)
        self.dump_stacks()
        if nthreads > 1:
            sys.stderr.write(sep)
        raise AssertionError('Timeout >%ss' % self.timeout)

    def timeout_thread(self, item, frame=None):
        """Dump stack of threads and call os._exit()

        This disables the capture manager before dumping the stacks of
        all threads.  After this os._exit(1) is called.
        """
        sep = '\n' + '+' * 10 + ' timeout ' + '+' * 10 + '\n'
        sep2 = '\n' + '-' * 10 + ' %s ' + '-' * 10 + '\n'
        sys.stderr.write(sep)
        capman = item.config.pluginmanager.getplugin('capturemanager')
        if capman:
            stdout, stderr = capman.suspendcapture(item)
            if stdout:
                sys.stderr.write(sep2 % 'stdout')
                sys.stderr.write(stdout)
            if stderr:
                sys.stderr.write(sep2 % 'stderr')
                sys.stderr.write(stderr)
        self.dump_stacks()
        sys.stderr.write(sep2 % 'stack of main thread')
        traceback.print_stack(frame)
        sys.stderr.write(sep)
        os._exit(1)

    def dump_stacks(self):
        """Dump the stacks of all threads except the current thread"""
        sep = '\n' + '-' * 10 + ' stack of thread %s ' + '-' * 10 + '\n'
        current_ident = threading.current_thread().ident
        for thread_ident, frame in sys._current_frames().iteritems():
            if thread_ident == current_ident:
                continue
            sys.stderr.write(sep % thread_id)
            traceback.print_stack(frame)
