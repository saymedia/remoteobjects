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

    def __init__(self, **kwargs):
        self._delivered = False
        self._http = None
        super(PromiseObject, self).__init__(**kwargs)

    @classmethod
    def get(cls, url, http=None, **kwargs):
        # Make a fake empty instance of this class.
        self = cls()
        self._id = url
        self._http = http

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

        if self._id is None:
            raise PromiseError('Instance %r has no URL from which to deliver' % (self,))

        response, content = self.get_response(self._id, self._http)
        self.update_from_response(response, content)

class Link(Property):

    """A RemoteObject property that lets RemoteObjects have attributes that are
    other unloaded RemoteObjects.

    Use this property when related content is not *part* of a RemoteObject, but
    is itself available at a relative URL to it. By default the target object's
    URL should be available at the property name relative to the owning
    instance's URL.

    For example:

    >>> class Item(RemoteObject):
    ...     feed = Link(Event)
    ...
    >>> i = Item.get('http://example.com/item/')
    >>> f = i.feed  # f's URL: http://example.com/item/feed

    Override a Link's `__get__` method to customize how the URLs to linked
    objects are constructed.

    """

    def __init__(self, cls, api_name=None, **kwargs):
        """Sets the RemoteObject class of the target resource (`cls`) and
        optionally the real relative URL of the resource.

        Optional parameter `api_name` is used as the link's relative URL. If
        not given, the name of the attribute to which the Link is assigned will
        be used.

        """
        self.cls = cls
        self.api_name = api_name
        super(Link, self).__init__(**kwargs)

    def install(self, attrname):
        """Installs the Link as a RemoteObject Property of the owning class."""
        if self.api_name is None:
            self.api_name = attrname
        return self

    def __get__(self, instance, owner):
        """Generates the RemoteObject for the target resource of this Link.

        By default, target resources are at a URL relative to the "parent"
        object's URL, named by the Link's `api_name`. Customize this method to
        define some other strategy for building links for your target API. The
        Link instance's `api_name` attribute will contain the specified in the
        declaration of the Link property.

        """
        if instance._id is None:
            raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (self.cls.__name__, owner.__name__))
        newurl = urlparse.urljoin(instance._id, self.api_name)
        return self.cls.get(newurl)

class ListObject(PromiseObject):

    """A RemoteObject representing a list of other RemoteObjects.

    ListObjects are for list endpoints in your target API that can be filtered
    by query parameter. A list of recent objects or a search can be modeled as
    ListObjects. Filtering a ListObject by a parameter returns a new copy of
    that ListObject that includes the new parameter.

    """

    def filter(self, **kwargs):
        """Returns a new ListObject that includes the current ListObject's
        filter, plus all the named parameters as query parameters.

        If your endpoint takes only certain parameters, or accepts parameters
        in some way other than query parameters in the URL, override this
        method to enforce your requirements.

        """
        parts = list(urlparse.urlparse(self._id))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])
        queryargs.update(kwargs)
        parts[4] = urllib.urlencode(queryargs)
        newurl = urlparse.urlunparse(parts)

        return self.get(newurl, http=self._http)

    def __getitem__(self, key):
        """Translates slice notation on a ListObject into `limit` and `offset` parameters."""
        if isinstance(key, slice):
            return self.filter(offset=key.start, limit=key.stop - key.start)
        raise IndexError('Items in a %s are not directly accessible' % (type(self).__name__,))
