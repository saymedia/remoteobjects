# Copyright (c) 2009-2010 Six Apart Ltd.
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

import unittest

import httplib2
import mox

from remoteobjects import fields, http, promise, listobject
from tests import test_dataobject, test_http
from tests import utils


class TestPageObjects(unittest.TestCase):

    cls = listobject.PageObject

    def test_slice_filter(self):

        class Toybox(self.cls):
            pass

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        b = Toybox.get('http://example.com/foo', http=h)
        self.assertEquals(b._location, 'http://example.com/foo')

        j = b[0:10]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._location, 'http://example.com/foo?limit=10&offset=0')

        j = b[300:370]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._location, 'http://example.com/foo?limit=70&offset=300')

        j = b[1:]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._location, 'http://example.com/foo?offset=1')

        j = b[:10]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._location, 'http://example.com/foo?limit=10')

        # Nobody did any HTTP, right?
        mox.Verify(h)

    def test_index(self):

        class Toybox(self.cls):
            pass

        url = 'http://example.com/whahay'
        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"entries":[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}"""
        h = utils.mock_http(request, content)
        mox.Replay(h)

        b = Toybox.get('http://example.com/whahay', http=h)
        self.assertEqual(b[7], 7)

        mox.Verify(h)        
