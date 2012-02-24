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

import py
import pytest


SIGALRM = getattr(signal, 'SIGALRM', None)


def pytest_addoption(parser):
    """Add options to control the timeout plugin"""
    group = parser.getgroup('timeout', 'Dump stacks after timeout')
    group.addoption('--timeout',
                    type=int,
                    default=300,
                    help='Timeout before dumping the traceback [300]')
    group.addoption('--nosigalrm',
                    action='store_true',
                    default=False,
                    help='Do not use SIGALRM, use a Timer thread instead')


def pytest_configure(config):
    """Activate timeout plugin if appropriate"""
    if config.getvalue('timeout') > 0:
        config.pluginmanager.register(FaultHandlerPlugin(config), 'timeout')


class FaultHandlerPlugin(object):
    """The timeout plugin"""

    def __init__(self, config):
        self.config = config
        self._current_timer = None
        self.cancel = None

    @property
    def timeout(self):
        return self.config.getvalue('timeout')

    def pytest_runtest_setup(self, item):
        """Setup up a timeout trigger and handler"""
        if SIGALRM and not self.config.getvalue('nosigalrm'):

            def handler(signum, frame):
                __tracebackhide__ = True
                self.timeout_sigalrm(item, frame)

            self.cancel = self.cancel_sigalrm
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(self.timeout)
        else:
            timer = threading.Timer(self.timeout, self.timeout_timer, (item,))
            self._current_timer = timer
            self.cancel = self.cancel_timer
            timer.start()

    def pytest_runtest_teardown(self):
        """Cancel the timeout trigger"""
        # When skipping is raised from a pytest_runtest_setup function
        # (as is the case when using the pytest.mark.skipif marker) we
        # may be called without our setup counterpart having been
        # called.  Hence the test for self.cancel.
        if self.cancel:
            self.cancel()
            self.cancel = None

    def cancel_sigalrm(self):
        signal.alarm(0)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

    def cancel_timer(self):
        self._current_timer.cancel()
        self._current_timer.join()
        self._current_timer = None

    def timeout_sigalrm(self, item, frame=None):
        """Dump stack of threads and raise an exception

        This will output the stacks of any threads other then the
        current to stderr and then raise an AssertionError, thus
        terminating the test.
        """
        __tracebackhide__ = True
        nthreads = len(threading.enumerate())
        if nthreads > 1:
            self.write_title('Timeout', sep='+')
        self.dump_stacks()
        if nthreads > 1:
            self.write_title('Timeout', sep='+')
        pytest.fail('Timeout >%ss' % self.timeout)

    def timeout_timer(self, item, frame=None):
        """Dump stack of threads and call os._exit()

        This disables the capturemanager and dumps stdout and stderr.
        Then the stacks are dumped and os._exit(1) is called.
        """
        try:
            capman = item.config.pluginmanager.getplugin('capturemanager')
            if capman:
                stdout, stderr = capman.suspendcapture(item)
            else:
                stdout, stderr = None
            self.write_title('Timeout', sep='+')
            caplog = item.config.pluginmanager.getplugin('_capturelog')
            if caplog and hasattr(item, 'capturelog_handler'):
                log = item.capturelog_handler.stream.getvalue()
                if log:
                    self.write_title('Captured log')
                    self.write(log)
            if stdout:
                self.write_title('Captured stdout')
                self.write(stdout)
            if stderr:
                self.write_title('Captured stderr')
                self.write(stderr)
            self.dump_stacks()
            self.write_title('Timeout', sep='+')
        except Exception:
            traceback.print_exc()
        finally:
            os._exit(1)

    def write_title(self, title, stream=None, sep='~'):
        """Write a section title

        If *stream* is None sys.stderr will be used, *sep* is used to
        draw the line.
        """
        if stream is None:
            stream = sys.stderr
        width = py.io.get_terminal_width()
        fill = int((width - len(title) - 2) / 2)
        line = ' '.join([sep * fill, title, sep * fill])
        if len(line) < width:
            line += sep * (width - len(line))
        stream.write('\n' + line + '\n')

    def write(self, text, stream=None):
        """Write text to stream

        Pretty stupid really, only here for symetry with .write_title().
        """
        if stream is None:
            stream = sys.stderr
        stream.write(text)

    def dump_stacks(self):
        """Dump the stacks of all threads except the current thread"""
        current_ident = threading.current_thread().ident
        for thread_ident, frame in sys._current_frames().iteritems():
            if thread_ident == current_ident:
                continue
            for t in threading.enumerate():
                if t.ident == thread_ident:
                    thread_name = t.name
                    break
            else:
                thread_name = '<unknown>'
            self.write_title('Stack of %s (%s)' % (thread_name, thread_ident))
            self.write(''.join(traceback.format_stack(frame)))
