import unittest

import httplib2
import mox

from remoteobjects import fields, http, promise, listobject
from tests import test_dataobject, test_http
from tests import utils


class TestListObjects(unittest.TestCase):

    cls = listobject.ListObject

    def testSliceFilter(self):

        class Toybox(listobject.ListObject):
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

    def testIndex(self):

        class Toybox(self.cls):
            pass

        url = 'http://example.com/whahay'
        headers = {"accept": "application/json"}
        request = dict(uri=url, headers=headers)
        content = """[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]"""
        h = utils.mock_http(request, content)
        mox.Replay(h)

        b = Toybox.get('http://example.com/whahay', http=h)
        self.assertEqual(b[7], 7)

        mox.Verify(h)        
