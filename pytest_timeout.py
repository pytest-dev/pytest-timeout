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
TIMEOUT_DESC = """
Timeout in seconds before dumping the stacks.  Default is 0 which
means no timeout.
""".strip()
METHOD_DESC = """
Timeout mechanism to use.  'signal' uses SIGALRM if available,
'thread' uses a timer thread.  The default is to use 'signal' and fall
back to 'thread'.
""".strip()


def pytest_addoption(parser):
    """Add options to control the timeout plugin"""
    group = parser.getgroup(
        'timeout', 'Interrupt test run and dump stacks of all threads after '
        'a test times out')
    group.addoption('--timeout',
                    type='int',
                    help=TIMEOUT_DESC)
    group.addoption('--timeout_method',
                    type='choice',
                    action='store',
                    choices=['signal', 'thread'],
                    help=METHOD_DESC)
    parser.addini('timeout', TIMEOUT_DESC)
    parser.addini('timeout_method', METHOD_DESC)


def pytest_configure(config):
    """Activate timeout plugin if appropriate"""
    # Note that this module is already registered under the "timeout"
    # name via setuptools' entry points.  So we need to use a
    # different name otherwise the plugin manager will assume the
    # module is already registered.
    if config.getvalue('timeout') is not None or config.getini('timeout'):
        config.pluginmanager.register(TimeoutPlugin(config), '_timeout')


class TimeoutPlugin(object):
    """The timeout plugin"""

    def __init__(self, config):
        self.config = config
        self._current_timer = None
        self.cancel = None

    def timeout(self, item):
        """Return the timeout for an item"""
        if 'timeout' in item.keywords:
            try:
                return int(item.keywords['timeout'].args[0])
            except KeyError:
                pass
            except ValueError:
                raise ValueError('Timeout marker must have integer argument')
        opt = item.config.getvalue('timeout')
        if opt is not None:
            return opt
        ini = item.config.getini('timeout')
        if ini:
            try:
                return int(ini)
            except ValueError:
                raise ValueError('Invalid timeout in ini config: %s' % ini)
        return 0

    def method(self, item):
        """Return the timeout method to be used for an item"""
        if 'timeout' in item.keywords:
            try:
                method = item.keywords['timeout'].kwargs['method']
            except KeyError:
                pass
            else:
                return self._validate_method(method, 'marker')
        cmdl = item.config.getvalue('timeout_method')
        if cmdl is not None:
            return self._validate_method(cmdl, 'command line')
        ini = item.config.getini('timeout_method')
        if ini:
            return self._validate_method(ini, 'configuration file')
        if SIGALRM:
            return 'signal'
        else:
            return 'thread'

    def _validate_method(self, method, where):
        if method not in ['signal', 'thread']:
            raise ValueError('Invalid method %s from %s' % (method, where))
        return method

    def pytest_runtest_setup(self, item):
        """Setup up a timeout trigger and handler"""
        if 'timeout' in item.keywords:
            marker = item.keywords['timeout']
            if len(marker.args) != 1:
                raise TypeError('Timeout marker must have exactly 1 argument')
            if marker.kwargs and list(marker.kwargs.keys()) != ['method']:
                raise TypeError(
                    'Timeout marker only takes the "method" keyword argument')

        timeout = self.timeout(item)
        if timeout <= 0:
            return
        method = self.method(item)
        if method == 'signal':

            def handler(signum, frame):
                __tracebackhide__ = True
                self.timeout_sigalrm(item, timeout)

            self.cancel = self.cancel_sigalrm
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
        elif method == 'thread':
            timer = threading.Timer(timeout,
                                    self.timeout_timer, (item, timeout))
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

    def timeout_sigalrm(self, item, timeout):
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
        pytest.fail('Timeout >%ss' % timeout)

    def timeout_timer(self, item, timeout):
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
            sys.stdout.flush()
            sys.stderr.flush()
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
        for thread_ident, frame in sys._current_frames().items():
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
