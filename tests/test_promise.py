from __future__ import with_statement

import httplib2
import unittest
import mox

from remoteobjects import tests, fields, remote, promise, PromiseObject
from remoteobjects.tests import test_dataobject, test_remote

class TestDataObjects(test_dataobject.TestDataObjects):
    @property
    def cls(self):
        return PromiseObject

class TestRemoteObjects(test_remote.TestRemoteObjects):
    @property
    def cls(self):
        return PromiseObject

class TestPromiseObjects(unittest.TestCase):
    @property
    def cls(self):
        return PromiseObject

    def testBasic(self):

        class Tiny(self.cls):
            name = fields.Something()

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        url = 'http://example.com/whahay'
        t = Tiny.get(url, http=h)

        # Check that we didn't do anything.
        mox.Verify(h)

        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"name": "Mollifred"}"""
        with tests.MockedHttp(request, content) as h:
            t._http = h  # inject, oops
            self.assertEquals(t.name, 'Mollifred')

class TestViews(unittest.TestCase):

    def testBasic(self):

        class Toy(PromiseObject):
            name = fields.Something()

        class Toybox(promise.View):
            entries = fields.List(fields.Object(Toy))

        h = mox.MockObject(httplib2.Http)
        mox.Replay(h)

        b = Toybox.get('http://example.com/foo', http=h)
        self.assertEquals(b._id, 'http://example.com/foo')

        x = b.filter(limit=10, offset=7)
        self.assert_(x is not b)
        self.assertEquals(b._id, 'http://example.com/foo')
        self.assertEquals(x._id, 'http://example.com/foo?limit=10&offset=7')

        y = b.filter(awesome='yes')
        self.assertEquals(y._id, 'http://example.com/foo?awesome=yes')
        y = y.filter(awesome='no')
        self.assertEquals(y._id, 'http://example.com/foo?awesome=no')

        j = b[0:10]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(j._id, 'http://example.com/foo?limit=10&offset=0')

        q = b[300:370]
        self.assert_(isinstance(j, Toybox))
        self.assertEquals(q._id, 'http://example.com/foo?limit=70&offset=300')

        self.assertRaises(IndexError, lambda: b[7])

        # Nobody did any HTTP, right?
        mox.Verify(h)

    def testAwesome(self):

        class Toy(PromiseObject):
            name = fields.Something()

        class Toybox(promise.View):
            entries = fields.List(fields.Object(Toy))

        class Room(PromiseObject):
            toybox = Toybox()

        r = Room.get('http://example.com/bwuh/')
        b = r.toybox
        self.assert_(isinstance(b, Toybox))
        self.assertEquals(b._id, 'http://example.com/bwuh/toybox')
