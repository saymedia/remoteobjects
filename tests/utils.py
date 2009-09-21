import httplib2
import logging
import os

import mox
import nose
import nose.tools


def todo(fn):
    @nose.tools.make_decorator(fn)
    def test_reverse(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        except:
            pass
        else:
            raise AssertionError('test %s unexpectedly succeeded' % fn.__name__)
    return test_reverse


def mock_http(req, resp_or_content):
    mock = mox.MockObject(httplib2.Http)

    if not isinstance(req, dict):
        req = dict(uri=req)

    def make_response(response, url):
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

    resp, content = make_response(resp_or_content, req['uri'])
    mock.request(**req).AndReturn((resp, content))
    mox.Replay(mock)
    return mock


def log():
    import sys
    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
