import time


def test_foo():
    print 'foo'
    time.sleep(10)
    print 'bar'
    assert False
