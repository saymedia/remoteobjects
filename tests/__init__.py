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
    def __init__(self, req_or_url, resp_or_content, **kwargs):
        self.mock = mox.MockObject(httplib2.Http)

        url,  req     = self.make_request(req_or_url, **kwargs)
        resp, content = self.make_response(resp_or_content, url)
        self.mock.request(url, **req).AndReturn((resp, content))

    def make_request(self, request, **kwargs):
        request_info = {}
        if isinstance(request, dict):
            url = request['url']
            del request['url']
            request_info.update(request)
        else:
            url = request
        request_info.update(kwargs)
        return url, request_info

    def make_response(self, response, url):
        default_response = {
            'status':           200,
            'etag':             '7',
            'content-type':     'application/json',
            'content-location': url,
        }

        if isinstance(response, dict):
            if 'content' in response:
                content = response['content']
                del response['content']
            else:
                content = ''

            status = response.get('status', 200)
            if 200 <= status < 300:
                response_info = dict(default_response)
                response_info.update(response)
            else:
                # Homg all bets are off!! Use specified headers only.
                response_info = dict(response)
        else:
            response_info = dict(default_response)
            content = response

        return httplib2.Response(response_info), content

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
