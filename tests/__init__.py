import logging
import httplib2
import mox

def skip(fn):
    def testNothing(self):
        self.assert_(True, 'skip this test')
    return testNothing

def todo(fn):
    def testReverse(self):
        try:
            fn(self)
        except:
            self.assert_(True, 'expected this test to fail')
        else:
            self.assert_(False, 'test unexpectedly succeeded')
    return testReverse

class MockedHttp(object):
    def __init__(self, url, content, **kwargs):
        resp = httplib2.Response({
            'status': 200,
            'etag': '7',
            'content-type': 'application/json',
            'content-location': url,
        })
        self.mock = mox.MockObject(httplib2.Http)

        self.mock.request(url, **kwargs).AndReturn((resp, content))

    def __enter__(self):
        mox.Replay(self.mock)
        return self.mock

    def __exit__(self, *exc_info):
        # don't really care about the mock if there was an exception
        if None in exc_info:
            mox.Verify(self.mock)

def log():
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
