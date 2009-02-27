from __future__ import with_statement

import unittest
import logging
import sys
from datetime import datetime

from remoteobjects import tests, fields, remote, DataObject, RemoteObject
from remoteobjects.tests import test_dataobject


# Ensure DataObject API is preserved.
class TestDataObjects(test_dataobject.TestDataObjects):
    @property
    def cls(self):
        return remote.RemoteObject


class TestBasic(unittest.TestCase):

    def testGet(self):

        class BasicMost(RemoteObject):
            name  = fields.Something()
            value = fields.Something()

        headers = {'accept': 'application/json'}
        content = """{"name": "Fred", "value": 7}"""
        with tests.MockedHttp('http://example.com/ohhai', content, headers=headers) as h:
            b = BasicMost.get('http://example.com/ohhai', http=h)

        self.assertEquals(b.name, 'Fred')
        self.assertEquals(b.value, 7)


    @tests.todo
    def testPost(self):
        raise NotImplementedError


    def testPut(self):

        class BasicMost(RemoteObject):
            name  = fields.Something()
            value = fields.Something()

        b = BasicMost()
        self.assertRaises(ValueError, lambda: b.put())

        headers = {'accept': 'application/json'}
        content = """{"name": "Molly", "value": 80}"""
        with tests.MockedHttp('http://example.com/bwuh', content, headers=headers) as h:
            b = BasicMost.get('http://example.com/bwuh', http=h)

        headers = {
            'accept':   'application/json',
            'if-match': '7',  # default etag
        }
        request  = dict(url='http://example.com/bwuh', method='PUT', headers=headers, body=content)
        response = dict(content=content, etag='xyz')
        with tests.MockedHttp(request, response) as h:
            b.put(http=h)

        self.assertEquals(b._etag, 'xyz')


    def testPutFailure(self):

        class BasicMost(RemoteObject):
            name  = fields.Something()
            value = fields.Something()

        headers = {'accept': 'application/json'}
        content = """{"name": "Molly", "value": 80}"""
        with tests.MockedHttp('http://example.com/bwuh', content, headers=headers) as h:
            b = BasicMost.get('http://example.com/bwuh', http=h)

        b.value = 'superluminal'

        headers = {
            'if-match': '7',  # default etag
            'accept':   'application/json',
        }
        content = """{"name": "Molly", "value": "superluminal"}"""
        request = dict(url='http://example.com/bwuh', method='PUT',
                       body=content, headers=headers)
        # Simulate a changed resource.
        response = dict(status=412)
        with tests.MockedHttp(request, response) as h:
            self.assertRaises(BasicMost.PreconditionFailed, lambda: b.put(http=h))


    def testDelete(self):

        class BasicMost(RemoteObject):
            name  = fields.Something()
            value = fields.Something()

        b = BasicMost()
        self.assertRaises(ValueError, lambda: b.put())

        headers = {'accept': 'application/json'}
        content = """{"name": "Molly", "value": 80}"""
        with tests.MockedHttp('http://example.com/bwuh', content, headers=headers) as h:
            b = BasicMost.get('http://example.com/bwuh', http=h)

        headers = {
            'accept':   'application/json',
            'if-match': '7',  # default etag
        }
        request  = dict(url='http://example.com/bwuh', method='DELETE', headers=headers)
        response = dict(status=204)
        with tests.MockedHttp(request, response) as h:
            b.delete(http=h)

        self.failIf(hasattr(b, '_id'))
        self.failIf(hasattr(b, '_etag'))


    def testNotFound(self):
        self.assert_(RemoteObject.NotFound)

        class Huh(RemoteObject):
            pass

        self.assert_(Huh.NotFound)

        headers = { 'accept': 'application/json' }
        response = {'content': '', 'status': 404}
        with tests.MockedHttp('http://example.com/bwuh', response, headers=headers) as http:
            self.assertRaises(Huh.NotFound, lambda: Huh.get('http://example.com/bwuh', http=http))


    @tests.todo
    def testNotFoundDiscrete(self):
        """Checks that the NotFound exceptions for different RemoteObjects are
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

        class Huh(RemoteObject):
            pass

        class What(RemoteObject):
            pass

        def tryThat(http):
            try:
                What.get('http://example.com/bwuh', http=http)
            # Let through What.NotFound only if it's not equivalent to Huh.NotFound.
            except Huh.NotFound:
                pass

        with tests.MockedHttp('http://example.com/bwuh', response, headers=headers) as http:
            self.assertRaises(What.NotFound, lambda: tryThat(http))


class TestLinks(unittest.TestCase):

    def testBasic(self):

        class What(RemoteObject):
            what = fields.Something()

        class Linky(RemoteObject):
            name  = fields.Something()
            stuff = remote.Link(r'asf', fields.Object(What))

        l = Linky(name='awesome')

        self.assertRaises(ValueError, l.stuff)

        l._id = 'http://example.com/dwar'

        self.assert_(callable(l.stuff), "Linky instance's stuff is a method")

        content = """{ "what": "what!" }"""
        headers = { 'accept': 'application/json' }
        with tests.MockedHttp('http://example.com/asf', content, headers=headers) as h:
            w = l.stuff(http=h)
        self.assert_(isinstance(w, What), 'stuff method gave us a What')
        self.assertEquals(w.what, 'what!', "stuff's What seems viable")
        self.assertEquals(w._id, 'http://example.com/asf', "stuff's What knows its _id")


    def testCallable(self):

        class What(RemoteObject):
            what = fields.Something()

        class Linky(RemoteObject):
            meh   = fields.Something()
            stuff = remote.Link(lambda o: o.meh, fields.Object(What))

        l = Linky(meh='http://example.com/bwuh')

        content = """{ "what": "wha-hay?" }"""
        headers = { 'accept': 'application/json' }
        with tests.MockedHttp('http://example.com/bwuh', content, headers=headers) as h:
            w = l.stuff(http=h)
        self.assert_(w)
        self.assertEquals(w.what, 'wha-hay?')
        self.assertEquals(w._id, 'http://example.com/bwuh')


if __name__ == '__main__':
    tests.log()
    unittest.main()
