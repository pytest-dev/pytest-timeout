"""Use the faulthandler module to catch hanging tests

This plugin uses the faulthandler module to dump the traceback of any
tests which hang longer then expected.  Optionally it allows you to
exit the process, though no cleanup will be performed in that case.
"""

import os
import signal
import sys
import threading
import traceback


def pytest_addoption(parser):
    """Add options to control the faulthandler and it's timeout"""
    group = parser.getgroup('faulthandler', 'Dump tracebacks after timeouts')
    group.addoption('--nofaulthandler',
                    dest='faulthandler',
                    action='store_false',
                    default=True,
                    help='Disable faulthandler usage')
    group.addoption('--faulthandler-timeout',
                    type=int,
                    default=300,
                    help='Timeout before dumping the traceback [300]')
    group.addoption('--faulthandler-exit',
                    action='store_true',
                    default=False,
                    help='Whether to call _exit(1) after the timeout [False]')


def pytest_configure(config):
    """Activate faulthandler plugin if appropriate"""
    if config.getvalue('faulthandler'):
        config.pluginmanager.register(FaultHandlerPlugin(config),
                                      '_faulthandler')


class FaultHandlerPlugin(object):
    """The faulthandler plugin"""

    def __init__(self, config):
        self.timeout = config.getvalue('faulthandler_timeout')
        self.exit = config.getvalue('faulthandler_exit')
        if not hasattr(signal, 'alarm'):
            self._current_timer = None

    def pytest_runtest_setup(self, item):
        """Setup up the faulthandler with a timeout"""
        if hasattr(signal, 'alarm'):

            def handler(signum, frame):
                assert signum == signal.SIGALRM
                self.dump_traceback(item, frame)

            signal.signal(signal.SIGALRM, handler)
            signal.alarm(self.timeout)

        else:
            timer = threading.Timer(self.timeout, self.dump_traceback, (item,))
            self._current_timer = timer
            timer.start()


    def pytest_runtest_teardown(self):
        """Cancel the faulthandler timeout"""
        if hasattr(signal, 'alarm'):
            signal.alarm(0)
        else:
            self._current_timer.cancel()

    def dump_traceback(self, item, frame=None):
        sep = '\n' + '+' * 10 + ' faulthandler ' + '+' * 10 + '\n'
        sep2 = '\n' + '-' * 10 + ' %s ' + '-' * 10 + '\n'
        sys.stderr.write(sep)
        capman = item.config.pluginmanager.getplugin('capturemanager')
        if capman and self.exit:
            stdout, stderr = capman.suspendcapture(item)
            if stdout:
                sys.stderr.write(sep2 % 'stdout')
                sys.stdout.write(stdout)
            if stderr:
                sys.stderr.write(sep2 % 'stderr')
                sys.stderr.write(stderr)
        sys.stderr.write(sep2 % 'stack of main thread')
        traceback.print_stack(frame)
        for thread_id, frame in sys._current_frames().iteritems():
            if thread_id == threading.current_thread().ident:
                continue
            sys.stderr.write(sep2 % 'stack of thread %s' % thread_id)
            traceback.print_stack(frame)
        sys.stderr.write(sep)
        if self.exit:
            os._exit(1)
        elif capman:
            capman.resumecapture_item(item)
