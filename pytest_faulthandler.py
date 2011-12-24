"""Use the faulthandler module to catch hanging tests

This plugin uses the faulthandler module to dump the traceback of any
tests which hang longer then expected.  Optionally it allows you to
exit the process, though no cleanup will be performed in that case.
"""

import faulthandler
import os
import sys
import threading


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
                    default=25,
                    help='Timeout before dumping the traceback [25]')
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
        self._current_timer = None

    def pytest_runtest_setup(self, item):
        """Setup up the faulthandler with a timeout"""
        # faulthandler.dump_tracebacks_later(self.timeout, exit=self.exit)
        timer = threading.Timer(self.timeout, self.dump_traceback, (item,))
        self._current_timer = timer
        timer.start()

    def pytest_runtest_teardown(self):
        """Cancel the faulthandler timeout"""
        # faulthandler.cancel_dump_tracebacks_later()
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None

    def dump_traceback(self, item):
        sep = '\n' + '+' * 10 + ' faulthandler ' + '+' * 10 + '\n'
        sys.stderr.write(sep)
        capman = item.config.pluginmanager.getplugin('capturemanager')
        if capman and self.exit:
            stdout, stderr = capman.suspendcapture(item)
            sys.stderr.write('\n' + '-' * 10 + ' stdout ' + '-' * 10 + '\n')
            sys.stdout.write(stdout)
            sys.stderr.write('\n' + '-' * 10 + ' stderr ' + '-' * 10 + '\n')
            sys.stderr.write(stderr)
            sys.stderr.write('\n' + '-' * 10 + ' threads ' + '-' * 10 + '\n')
        faulthandler.dump_traceback()
        sys.stderr.write(sep)
        if self.exit:
            os._exit(1)
        elif capman:
            capman.resumecapture_item(item)
