from remoteobjects import RemoteObject
from tests import test_dataobject, test_http, test_promise


class TestDataObjects(test_dataobject.TestDataObjects):

    cls = RemoteObject


class TestHttpObjects(test_http.TestHttpObjects):

    cls = RemoteObject


class TestPromiseObjects(test_promise.TestPromiseObjects):

    cls = RemoteObject
