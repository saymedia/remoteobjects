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

from remoteobjects import fields, listobject, promise
from tests import utils


class TestPageObjects(unittest.TestCase):

    cls = listobject.PageObject

    def test_slice_filter(self):

        class Toybox(self.cls):
            pass

        h = mock.NonCallableMock(spec_set=httplib2.Http)

        b = Toybox.get('http://example.com/foo', http=h)
        self.assertEqual(b._location, 'http://example.com/foo')

        j = b[0:10]
        self.assertIsInstance(j, Toybox)
        self.assertEqual(j._location, 'http://example.com/foo?limit=10&offset=0')

        j = b[300:370]
        self.assertIsInstance(j, Toybox)
        self.assertEqual(j._location, 'http://example.com/foo?limit=70&offset=300')

        j = b[1:]
        self.assertIsInstance(j, Toybox)
        self.assertEqual(j._location, 'http://example.com/foo?offset=1')

        j = b[:10]
        self.assertIsInstance(j, Toybox)
        self.assertEqual(j._location, 'http://example.com/foo?limit=10')

        # Nobody did any HTTP, right?
        self.assertEqual([], h.method_calls)

    def test_index(self):

        class Toybox(self.cls):
            pass

        url = 'http://example.com/whahay'
        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """{"entries":[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}"""
        h = utils.mock_http(request, content)

        b = Toybox.get('http://example.com/whahay', http=h)
        self.assertEqual(b[7], 7)

        h.request.assert_called_once_with(**request)


class TestPageOf(unittest.TestCase):

    def test_basemodule(self):
        # When creating PageOf(myclass), it should use PageObject as superclass
        self.assertEqual(listobject.PageOf._basemodule, listobject.PageObject)

    def test_to_dict(self):
        class MyObj(promise.PromiseObject):
            myfield = fields.Field()
        MyObjPage = listobject.PageOf(MyObj)
        obj = MyObjPage(entries=[MyObj(myfield="myval")])
        # When creating PageOf(myclass), it should use PageObject as superclass
        self.assertIsInstance(obj, listobject.PageObject)
        self.assertEqual({"entries": [{"myfield": "myval"}]}, obj.to_dict())

    def test_from_dict(self):
        class MyObj(promise.PromiseObject):
            myfield = fields.Field()
        MyObjPage = listobject.PageOf(MyObj)
        actual = MyObjPage.from_dict({"entries": [{"myfield": "myval"}]})
        self.assertIsInstance(actual, listobject.PageObject)
        self.assertEqual("myval", actual.entries[0].myfield)
        expected = MyObjPage(entries=[MyObj(myfield="myval")])
        self.assertEqual(actual, expected)


class TestListOf(unittest.TestCase):

    def test_basemodule(self):
        # When creating ListOf(myclass), it should use ListObject as superclass
        self.assertEqual(listobject.ListOf._basemodule, listobject.ListObject)

    def test_to_dict(self):
        class MyObj(promise.PromiseObject):
            myfield = fields.Field()
        MyObjList = listobject.ListOf(MyObj)
        obj = MyObjList(entries=[MyObj(myfield="myval")])
        # When creating ListOf(myclass), it should use ListObject as superclass
        self.assertIsInstance(obj, listobject.ListObject)
        self.assertEqual([{"myfield": "myval"}], obj.to_dict())

    def test_from_dict(self):
        class MyObj(promise.PromiseObject):
            myfield = fields.Field()
        MyObjList = listobject.ListOf(MyObj)
        actual = MyObjList.from_dict([{"myfield": "myval"}])
        expected = MyObjList(entries=[MyObj(myfield="myval")])
        self.assertEqual("myval", actual.entries[0].myfield)
        self.assertIsInstance(actual, listobject.ListObject)
        self.assertEqual(actual, expected)
