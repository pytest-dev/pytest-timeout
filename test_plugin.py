import threading
import time


def test_foo():
    print 'foo'
    time.sleep(10)
    print 'bar'
    assert False


def test_thread():
    t = threading.Thread(target=time.sleep, args=(10,))
    t.daemon = True
    t.start()
    print 'foo'
    time.sleep(10)
    print 'bar'
    assert False
