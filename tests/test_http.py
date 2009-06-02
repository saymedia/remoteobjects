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
    @property
    def cls(self):
        return http.HttpObject


class TestHttpObjects(unittest.TestCase):

    @property
    def cls(self):
        return http.HttpObject


    def testGet(self):

        class BasicMost(self.cls):
            name  = fields.Field()
            value = fields.Field()

        request = {
            'uri': 'http://example.com/ohhai',
            'headers': {'accept': 'application/json'},
        }
        content = """{"name": "Fred", "value": 7}"""

        h = utils.mock_http(request, content)
        b = BasicMost.get('http://example.com/ohhai', http=h)
        self.assertEquals(b.name, 'Fred')
        self.assertEquals(b.value, 7)
        mox.Verify(h)


    def testPost(self):

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

        headers = {'accept': 'application/json'}
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


    def testPut(self):

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
            'accept':   'application/json',
            'if-match': '7',  # default etag
        }
        request  = dict(uri='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        h = utils.mock_http(request, response)
        b.put(http=h)
        mox.Verify(h)

        self.assertEquals(b._etag, 'xyz')


    def testPutFailure(self):

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
            'if-match': '7',  # default etag
            'accept':   'application/json',
        }
        content = """{"name": "Molly", "value": "superluminal"}"""
        request = dict(uri='http://example.com/bwuh', method='PUT',
                       body=content, headers=headers)
        # Simulate a changed resource.
        response = dict(status=412)
        h = utils.mock_http(request, response)
        self.assertRaises(BasicMost.PreconditionFailed, lambda: b.put(http=h))
        mox.Verify(h)


    def testDelete(self):

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


    def testDeleteFailure(self):

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


    def testNotFound(self):
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
    def testNotFoundDiscrete(self):
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

        def tryThat(http):
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
        self.assertRaises(What.NotFound, lambda: tryThat(http))
        mox.Verify(http)


if __name__ == '__main__':
    utils.log()
    unittest.main()
