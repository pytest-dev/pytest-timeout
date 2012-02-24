pytest-timeout
==============

This is a plugin which will terminate tests after a certain timeout.
When doing so you will get a stack dump of all threads running at the
time.  This is useful when e.g. running tests under a continuous
integration (CI) server.


Usage
-----

Install via::

   pip install pytest-timeout

and then enable the plugin, either from the command line::

   py.test -p timeout

or more conveniently from within the test module or conftest.py::

   pytest_plugins = 'timeout'


You can change the timeout using the `--timeout` parameter which sets
the timeout in seconds.


How It Works
------------

This plugin works in one of two ways.  If the system supports the
SIGALRM signal an alarm will be scheduled when the tests starts and
cancelled when it finishes.  If the alarm expires during the test the
signal handler will use `pytest.fail()` to interrupt the test after
having dumped the stack of any other threads running to stderr.

If the system does not support SIGALRM or the `--nosigalrm` option was
used then a timer thread will be used instead.  Once more, if this
timer is not cancelled before it expires it will dump the stack of all
threads to stderr before terminating the entire py.test process using
os._exit(1).

The downside of the SIGALRM method is that the signal is used by the
test framework.  If this signal is used by the code under test you
will need to use the `--nosigalrm` option.  The limitation of the
timer thread however is the extra overhead of creating a thread for
each executed test and the fact that after one timeout the entire
process is stopped and no further tests are executed.
