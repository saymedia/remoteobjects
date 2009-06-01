from __future__ import with_statement

import unittest

import httplib2
import mox

from remoteobjects import fields, http, promise
from tests import test_dataobject, test_http
from tests import utils


class TestDataObjects(test_dataobject.TestDataObjects):
    @property
    def cls(self):
        return promise.PromiseObject


class TestHttpObjects(test_http.TestHttpObjects):
    @property
    def cls(self):
        return promise.PromiseObject


class TestPromiseObjects(unittest.TestCase):
    @property
    def cls(self):
        return promise.PromiseObject

    def testBasic(self):

        class Tiny(self.cls):
            name = fields.Field()

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        url = 'http://example.com/whahay'
        t = Tiny.get(url, http=h)

        # Check that we didn't do anything.
        mox.Verify(h)

        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"name": "Mollifred"}"""
        with utils.MockedHttp(request, content) as h:
            t._http = h  # inject, oops
            self.assertEquals(t.name, 'Mollifred')


class TestViews(unittest.TestCase):

    def testBasic(self):

        class Toy(promise.PromiseObject):
            name = fields.Field()

        class Toybox(promise.ListObject):
            entries = fields.List(fields.Object(Toy))

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        b = Toybox.get('http://example.com/foo', http=h)
        self.assertEquals(b._location, 'http://example.com/foo')

        x = b.filter(limit=10, offset=7)
        self.assert_(x is not b)
        self.assertEquals(b._location, 'http://example.com/foo')
        self.assertEquals(x._location, 'http://example.com/foo?limit=10&offset=7')

        y = b.filter(awesome='yes')
        self.assertEquals(y._location, 'http://example.com/foo?awesome=yes')
        y = y.filter(awesome='no')
        self.assertEquals(y._location, 'http://example.com/foo?awesome=no')

        j = b[0:10]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._location, 'http://example.com/foo?limit=10&offset=0')

        q = b[300:370]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(q._location, 'http://example.com/foo?limit=70&offset=300')

        # Can't use a non-slice on a plain ListObject
        self.assertRaises(TypeError, lambda: b[7])

        # Nobody did any HTTP, right?
        mox.Verify(h)

    def testAwesome(self):

        class Toy(promise.PromiseObject):
            name = fields.Field()

        class Toybox(promise.ListObject):
            entries = fields.List(fields.Object(Toy))

        class Room(promise.PromiseObject):
            toybox = fields.Link(Toybox)

        r = Room.get('http://example.com/bwuh/')
        b = r.toybox
        self.assert_(isinstance(b, Toybox))
        self.assertEquals(b._location, 'http://example.com/bwuh/toybox')
