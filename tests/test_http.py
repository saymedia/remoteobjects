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

from remoteobjects import fields, http
from six import PY2
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
        self.assertEqual(b.name, 'Fred')
        self.assertEqual(b.value, 7)
        h.request.assert_called_once_with(**request)

    def test_get_bad_encoding(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/ohhai',
            'headers': {'accept': 'application/json'},
        }
        content = b"""{"name": "Fred\xf1", "value": "image by \xefrew Example"}"""

        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        self.assertEqual(b.name, u"Fred\ufffd")
        # Bad characters are replaced with the unicode Replacement Character 0xFFFD.
        self.assertEqual(b.value, u"image by \ufffdrew Example")
        h.request.assert_called_once_with(**request)
        h.reset_mock()

        # since simplejson 3.3.0, lone surrogates are passed through
        # https://github.com/simplejson/simplejson/commit/35816bfe2d0ddeb5ddcc68239683cbb35b7e3ff2
        content = """{"name": "lone surrogate \\ud800", "value": "\\udc00 lone surrogate"}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        # Lone surrogates are passed through as lone surrogates in the python unicode value
        self.assertEqual(b.name, u"lone surrogate \ud800")
        self.assertEqual(b.value, u"\udc00 lone surrogate")
        h.request.assert_called_once_with(**request)

        content = u"""{"name": "100 \u20AC", "value": "13000 \u00A5"}""".encode('utf-8')
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        # JSON containing non-ascii UTF-8 should be decoded to unicode strings
        self.assertEqual(b.name, u"100 \u20AC")
        self.assertEqual(b.value, u"13000 \u00A5")
        h.request.assert_called_once_with(**request)

        content = b"""{"name": "lone surrogate \xed\xa0\x80", "value": "\xed\xb0\x80 lone surrogate"}"""
        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        # Lone surrogates are passed through as lone surrogates in the python unicode value
        if PY2:
            # in python2, our JSONDecoder does not detect naked lone surrogates
            self.assertEqual(b.name, u"lone surrogate \ud800")
            self.assertEqual(b.value, u"\udc00 lone surrogate")
        else:
            # in python3, bytes.decode replaces lone surrogates with replacement char
            self.assertEqual(b.name, u"lone surrogate \ufffd\ufffd\ufffd")
            self.assertEqual(b.value, u"\ufffd\ufffd\ufffd lone surrogate")

        h.request.assert_called_once_with(**request)

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
        self.assertEqual(c.name, 'CBS')
        h.request.assert_called_once_with(**request)

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
        h.request.assert_called_once_with(**request)

        self.assertEqual(b._location, 'http://example.com/fred')
        self.assertEqual(b._etag, 'xyz')

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
        self.assertEqual(b.name, 'Molly')
        h.request.assert_called_once_with(**request)

        headers = {
            'accept':       'application/json',
            'content-type': 'application/json',
            'if-match':     '7',  # default etag
        }
        request  = dict(uri='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        h = utils.mock_http(request, response)
        b.put(http=h)
        h.request.assert_called_once_with(**request)

        self.assertEqual(b._etag, 'xyz')

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
        self.assertEqual(b.name, 'Molly')
        h.request.assert_called_once_with(**request)

        headers = {
            'accept':       'application/json',
            'content-type': 'application/json',
            'if-match': '7',
        }
        request  = dict(uri='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content="", status=204)
        h = utils.mock_http(request, response)
        b.put(http=h)
        h.request.assert_called_once_with(**request)

        self.assertEqual(b.name, 'Molly')

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
        self.assertEqual(b.value, 80)
        h.request.assert_called_once_with(**request)

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
        h.request.assert_called_once_with(**request)

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
        self.assertEqual(b.value, 80)
        h.request.assert_called_once_with(**request)

        headers = {
            'accept':   'application/json',
            'if-match': '7',  # default etag
        }
        request  = dict(uri='http://example.com/bwuh', method='DELETE', headers=headers)
        response = dict(status=204)
        h = utils.mock_http(request, response)
        b.delete(http=h)
        h.request.assert_called_once_with(**request)

        self.assertFalse(b._location is not None)
        self.assertFalse(hasattr(b, '_etag'))

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
        h.request.assert_called_once_with(**request)

    def test_not_found(self):
        self.assertTrue(self.cls.NotFound)

        class Huh(self.cls):
            name = fields.Field()

        self.assertTrue(Huh.NotFound)

        request = {
            'uri': 'http://example.com/bwuh',
            'headers': {'accept': 'application/json'},
        }
        response = {'content': '', 'status': 404}
        http = utils.mock_http(request, response)
        self.assertRaises(Huh.NotFound, lambda: Huh.get('http://example.com/bwuh', http=http).name)
        http.request.assert_called_once_with(**request)

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
        http = utils.mock_http(request, response)
        self.assertRaises(What.NotFound, lambda: try_that(http))
        http.request.assert_called_once_with(**request)


if __name__ == '__main__':
    utils.log()
    unittest.main()
