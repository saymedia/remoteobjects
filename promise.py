import urlparse
import urllib
import cgi

from remoteobjects.remote import RemoteObject
from remoteobjects.fields import Property

class PromiseError(Exception):
    pass

class PromiseObject(RemoteObject):
    """A RemoteObject that delays actual retrieval of the remote resource until
    required by the use of its data.

    A PromiseObject is only "promised" to the caller until its data is used.
    When the caller tries to use attributes that should have data in them from
    the remote resource, only *then* is the resource actually fetched.

    """

    @classmethod
    def get(cls, url, http=None, **kwargs):
        # Make a fake empty instance of this class.
        self = cls()
        self._id = url
        self._http = http
        self._delivered = False

        return self

    def __getattr__(self, attr):
        if attr in self.fields:
            # Oops, that's data. Try delivering it?
            if not self._delivered:
                self.deliver()
                if attr in self.__dict__:
                    return self.__dict__[attr]

        # attr is not a field, or even delivering the object didn't set it.
        raise AttributeError, 'Instance %r has no such attribute %r' % (self, attr)

    def deliver(self):
        if self._delivered:
            raise PromiseError('%s instance %r has already been delivered' % (type(self).__name__, self))
        self._delivered = True  # ambitious

        response, content = self.get_response(self._id, self._http)
        self.update_from_response(response, content)

class View(PromiseObject, Property):

    def __init__(self, api_name=None):
        self.api_name = api_name

    def install(self, attrname):
        if self.api_name is None:
            self.api_name = attrname
        return self

    def __get__(self, instance, owner):
        if instance._id is None:
            raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (type(self).__name__, owner.__name__))
        newurl = urlparse.urljoin(instance._id, self.api_name)
        return type(self).get(newurl)

    def filter(self, **kwargs):
        parts = list(urlparse.urlparse(self._id))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])
        queryargs.update(kwargs)
        parts[4] = urllib.urlencode(queryargs)
        newurl = urlparse.urlunparse(parts)
        return type(self).get(newurl, http=self._http)

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self.filter(offset=key.start, limit=key.stop - key.start)
        raise IndexError('Items in a %s are not directly accessible' % (type(self).__name__,))
