# Copyright (c) 2009 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
