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
import mock

from remoteobjects import fields, promise
from tests import test_dataobject, test_http
from tests import utils


class TestDataObjects(test_dataobject.TestDataObjects):

    cls = promise.PromiseObject


class TestHttpObjects(test_http.TestHttpObjects):

    cls = promise.PromiseObject


class TestPromiseObjects(unittest.TestCase):

    cls = promise.PromiseObject

    def test_basic(self):

        class Tiny(self.cls):
            name = fields.Field()

        h = mock.NonCallableMock(spec_set=httplib2.Http)

        url = 'http://example.com/whahay'
        t = Tiny.get(url, http=h)

        # Check that we didn't do anything.
        self.assertEqual([], h.method_calls)

        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"name": "Mollifred"}"""
        h = utils.mock_http(request, content)
        t._http = h

        self.assertEqual(t.name, 'Mollifred')
        h.request.assert_called_once_with(**request)

    def test_filter(self):

        class Toy(self.cls):
            name = fields.Field()

        h = mock.NonCallableMock(spec_set=httplib2.Http)

        b = Toy.get('http://example.com/foo', http=h)
        self.assertEqual(b._location, 'http://example.com/foo')

        x = b.filter(limit=10, offset=7)
        self.assertTrue(x is not b)
        self.assertEqual(b._location, 'http://example.com/foo')
        self.assertEqual(x._location, 'http://example.com/foo?limit=10&offset=7')

        y = b.filter(awesome='yes')
        self.assertEqual(y._location, 'http://example.com/foo?awesome=yes')
        y = y.filter(awesome='no')
        self.assertEqual(y._location, 'http://example.com/foo?awesome=no')

        # Nobody did any HTTP, right?
        self.assertEqual([], h.method_calls)

    def test_filter_mix_str_unicode(self):
        """On python2, test that filter accepts both unicode and str"""
        class Toy(self.cls):
            name = fields.Field()

        h = mock.NonCallableMock(spec_set=httplib2.Http)

        b = Toy.get('http://example.com/foo', http=h)
        self.assertEqual(b._location, 'http://example.com/foo')

        y = b.filter(a='a', b=u'b')
        self.assertEqual(y._location, 'http://example.com/foo?a=a&b=b')
        y = b.filter(**{'a': 'a', u'b': u'b'})
        self.assertEqual(y._location, 'http://example.com/foo?a=a&b=b')


    def test_awesome(self):

        class Toy(self.cls):
            name = fields.Field()

        class Room(self.cls):
            toybox = fields.Link(Toy)

        r = Room.get('http://example.com/bwuh/')
        b = r.toybox
        self.assertIsInstance(b, Toy)
        self.assertEqual(b._location, 'http://example.com/bwuh/toybox')

    def test_set_before_delivery(self):

        class Toy(self.cls):
            names = fields.List(fields.Field())
            foo = fields.Field()

        url = 'http://example.com/whahay'
        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"names": ["Mollifred"], "foo":"something"}"""
        h = utils.mock_http(request, content)

        # test case where attribute is assigned to object ahead of delivery
        t = Toy.get(url, http=h)
        t.names = ["New name"]
        d = t.to_dict() # this delivers the object

        # self.assertEqual(t.foo, "something")
        self.assertEqual(d['names'][0], "New name")
        self.assertEqual(t.names[0], "New name")

        h = utils.mock_http(request, content)
        # test case where we update_from_dict explictly after setting attributes
        t = Toy.get(url, http=h)
        t.foo = "local change"
        t.update_from_dict({"names": ["local update"]})

        self.assertEqual(t.foo, None)
