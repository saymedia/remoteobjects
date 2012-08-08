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

from datetime import datetime
import logging
import sys
import unittest

import mox

from remoteobjects import fields, http
from tests import test_dataobject
from tests import utils


# Ensure DataObject API is preserved.
class TestDataObjects(test_dataobject.TestDataObjects):

    cls = http.HttpObject


class TestHttpObjects(unittest.TestCase):

    cls = http.HttpObject

    def test_get(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/ohhai',
            'headers': {'accept': 'application/json', 'x-test': 'boo'},
        }
        content = """{"name": "Fred", "value": 7}"""

        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h,
                          headers={"x-test": "boo"})
        self.assertEquals(b.name, 'Fred')
        self.assertEquals(b.value, 7)
        mox.Verify(h)

    def test_get_bad_encoding(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/ohhai',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Fred\xf1", "value": "image by \xefrew Example"}"""

        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        self.assertEquals(b.name, u"Fred\ufffd")
        # Bad characters are replaced with the unicode Replacement Character 0xFFFD.
        self.assertEquals(b.value, u"image by \ufffdrew Example")
        mox.Verify(h)

    def test_post(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        class ContainerMost(self.cls):
            name = fields.Field()

        request = {
            'uri': 'http://example.com/asfdasf',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "CBS"}"""
        h = utils.mock_http(request, content)
        c = ContainerMost.get('http://example.com/asfdasf', http=h)
        self.assertEquals(c.name, 'CBS')
        mox.Verify(h)

        b = BasicMost(name='Fred Friendly', value=True)

        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
        }
        content = """{"name": "Fred Friendly", "value": true}"""
        request = dict(uri='http://example.com/asfdasf', method='POST',
                       body=content, headers=headers)
        response = dict(content=content, status=201, etag='xyz',
                        location='http://example.com/fred')
        h = utils.mock_http(request, response)
        c.post(b, http=h)
        mox.Verify(h)

        self.assertEquals(b._location, 'http://example.com/fred')
        self.assertEquals(b._etag, 'xyz')

    def test_put(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost()
        self.assertRaises(ValueError, lambda: b.put())

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Molly", "value": 80}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/bwuh', http=h)
        self.assertEquals(b.name, 'Molly')
        mox.Verify(h)

        headers = {
            'accept':       'application/json',
            'content-type': 'application/json',
            'if-match':     '7',  # default etag
        }
        request  = dict(uri='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        h = utils.mock_http(request, response)
        b.put(http=h)
        mox.Verify(h)

        self.assertEquals(b._etag, 'xyz')

    def test_put_no_content(self):
        """
        Don't try to update from a no-content response.

        """

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Molly", "value": 80}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/bwuh', http=h)
        self.assertEquals(b.name, 'Molly')
        mox.Verify(h)

        headers = {
            'accept':       'application/json',
            'content-type': 'application/json',
            'if-match': '7',
        }
        request  = dict(uri='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content="", status=204)
        h = utils.mock_http(request, response)
        b.put(http=h)
        mox.Verify(h)

        self.assertEquals(b.name, 'Molly')

    def test_put_failure(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Molly", "value": 80}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/bwuh', http=h)
        self.assertEquals(b.value, 80)
        mox.Verify(h)

        b.value = 'superluminal'

        headers = {
            'accept':       'application/json',
            'content-type': 'application/json',
            'if-match':     '7',  # default etag
        }
        content = """{"name": "Molly", "value": "superluminal"}"""
        request = dict(uri='http://example.com/bwuh', method='PUT',
                       body=content, headers=headers)
        # Simulate a changed resource.
        response = dict(status=412)
        h = utils.mock_http(request, response)
        self.assertRaises(BasicMost.PreconditionFailed, lambda: b.put(http=h))
        mox.Verify(h)

    def test_delete(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost()
        self.assertRaises(ValueError, lambda: b.put())

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Molly", "value": 80}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/bwuh', http=h)
        self.assertEquals(b.value, 80)
        mox.Verify(h)

        headers = {
            'accept':   'application/json',
            'if-match': '7',  # default etag
        }
        request  = dict(uri='http://example.com/bwuh', method='DELETE', headers=headers)
        response = dict(status=204)
        h = utils.mock_http(request, response)
        b.delete(http=h)
        mox.Verify(h)

        self.failIf(b._location is not None)
        self.failIf(hasattr(b, '_etag'))

    def test_delete_failure(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        b = BasicMost(name='Molly', value=80)
        b._location = 'http://example.com/bwuh'
        b._etag = 'asfdasf'

        headers = {
            'accept':   'application/json',
            'if-match': 'asfdasf',
        }
        request  = dict(uri='http://example.com/bwuh', method='DELETE', headers=headers)
        response = dict(status=412)  # Precondition Failed

        h = utils.mock_http(request, response)
        self.assertRaises(BasicMost.PreconditionFailed, lambda: b.delete(http=h))
        mox.Verify(h)

    def test_not_found(self):
        self.assert_(self.cls.NotFound)

        class Huh(self.cls):
            name = fields.Field()

        self.assert_(Huh.NotFound)

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        response = {'content': '', 'status': 404}
        http = utils.mock_http(request, response)
        self.assertRaises(Huh.NotFound, lambda: Huh.get('http://example.com/bwuh', http=http).name)
        mox.Verify(http)

    @utils.todo
    def test_not_found_discrete(self):
        """Checks that the NotFound exceptions for different HttpObjects are
        really different classes, so you can catch them discretely and treat
        different unfound objects differently, like:

        >>> try:
        ...     h = Huh.get(huh_url)
        ...     w = What.get(what_url)
        ... except Huh.NotFound:
        ...     # oops, no Huh
        ... except What.NotFound:
        ...     # oops, no What

        This feature is not implemented.

        """

        class Huh(self.cls):
            pass

        class What(self.cls):
            pass

        def try_that(http):
            try:
                What.get('http://example.com/bwuh', http=http)
            # Let through What.NotFound only if it's not equivalent to Huh.NotFound.
            except Huh.NotFound:
                pass

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        response = dict(status=404)
        http = utils.MockedHttp(request, response)
        self.assertRaises(What.NotFound, lambda: try_that(http))
        mox.Verify(http)


if __name__ == '__main__':
    utils.log()
    unittest.main()
