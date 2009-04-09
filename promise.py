import urlparse
import urllib
import cgi

from remoteobjects.remote import RemoteObject
from remoteobjects.fields import Property

class PromiseError(Exception):
    """An exception representing an error promising or delivering a
    `PromiseObject` instance."""
    pass

class PromiseObject(RemoteObject):
    """A `RemoteObject` that delays actual retrieval of the remote resource until
    required by the use of its data.

    A PromiseObject is only "promised" to the caller until its data is used.
    When the caller tries to use attributes that should have data in them from
    the remote resource, only *then* is the resource actually fetched.

    """

    def __init__(self, **kwargs):
        """Initializes a `PromiseObject` as undelivered."""
        self._delivered = False
        self._http = None
        super(PromiseObject, self).__init__(**kwargs)

    @classmethod
    def get(cls, url, http=None, **kwargs):
        """Creates a new `PromiseObject` instance that, when delivered, will
        contain the data at the given URL."""
        # Make a fake empty instance of this class.
        self = cls()
        self._location = url
        self._http = http

        return self

    def __getattr__(self, attr):
        """Returns the value of the requested attribute, after attempting to
        deliver the `PromiseObject` if necessary.

        If the instance is undelivered and the requested attribute is a
        declared field of the instance's class, `__getattr__` attempts to
        deliver the object before 

        Because delivery is only attempted on an attribute "miss," all the
        exceptions that `RemoteObject.get()` may raise may be raised through
        attribute access on a `PromiseObject`.

        """
        if attr in self.fields:
            # Oops, that's data. Try delivering it?
            if not self._delivered:
                self.deliver()
                if attr in self.__dict__:
                    return self.__dict__[attr]

        # attr is not a field, or even delivering the object didn't set it.
        raise AttributeError, 'Instance %r has no such attribute %r' % (self, attr)

    def deliver(self):
        """Attempts to fill the instance with the data it represents.

        If the instance has already been delivered or the instance has no URL
        from which to fetch data, `deliver()` raises a `PromiseError`. Other
        exceptions from requesting and decoding a `RemoteObject` that might
        normally result from a `RemoteObject.get()` may also be thrown.

        """
        if self._delivered:
            raise PromiseError('%s instance %r has already been delivered' % (type(self).__name__, self))
        if self._location is None:
            raise PromiseError('Instance %r has no URL from which to deliver' % (self,))

        response, content = self.get_response(self._location, self._http)
        self.update_from_response(self._location, response, content)

    def update_from_response(self, url, response, content):
        """Fills the `PromiseObject` instance with the data from the given
        HTTP response and if successful marks the instance delivered."""
        super(PromiseObject, self).update_from_response(url, response, content)
        # Any updating from a response constitutes delivery.
        self._delivered = True

# TODO: move this to fields.py?
class Link(Property):

    """A `RemoteObject` property representing a "link" from one `RemoteObject`
    instance to another.

    Use this property when related content is not *part* of a RemoteObject,
    but is instead available at a URL relative to it. By default the target
    object's URL should be available at the property name relative to the
    owning instance's URL.

    For example:

    >>> class Item(RemoteObject):
    ...     feed = Link(Event)
    ...
    >>> i = Item.get('http://example.com/item/')
    >>> f = i.feed  # f's URL: http://example.com/item/feed

    Override the `__get__` method of a `Link` subclass to customize how the
    URLs to linked objects are constructed.

    """

    def __init__(self, cls, api_name=None, **kwargs):
        """Sets the `RemoteObject` class of the target resource and,
        optionally, the real relative URL of the resource.

        Optional parameter `api_name` is used as the link's relative URL. If
        not given, the name of the attribute to which the Link is assigned
        will be used.

        """
        self.cls = cls
        self.api_name = api_name
        super(Link, self).__init__(**kwargs)

    def install(self, attrname):
        """Installs the `Link` instance as an attribute of the `RemoteObject`
        class in which it was declared."""
        if self.api_name is None:
            self.api_name = attrname
        return self

    def __get__(self, instance, owner):
        """Generates the RemoteObject for the target resource of this Link.

        By default, target resources are at a URL relative to the "parent"
        object's URL, named by the `api_name` attribute of the `Link`
        instance. Override this method to define some other strategy for
        building links for your target API.

        """
        if instance._location is None:
            raise AttributeError('Cannot find URL of %s relative to URL-less %s' % (self.cls.__name__, owner.__name__))
        newurl = urlparse.urljoin(instance._location, self.api_name)
        return self.cls.get(newurl)

class ListObject(PromiseObject):

    """A `RemoteObject` representing a list of other `RemoteObject` instances.

    `ListObject` instances can be filtered by options that are passed to your
    target API, such as a list of recent objects or a search. Filtering a
    ListObject by a parameter returns a new copy of that ListObject that
    includes the new parameter.

    """

    def filter(self, **kwargs):
        """Returns a new `ListObject` instance that uses the filter of the
        current `ListObject` instance plus all the given keyword parameters.

        By default, all filter parameters are given as named parameters in the
        query string.

        If your endpoint takes only certain parameters, or accepts parameters
        in some way other than query parameters in the URL, override this
        method to build the URL and return the new `ListObject` instance as
        you require.

        """
        parts = list(urlparse.urlparse(self._location))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])
        queryargs.update(kwargs)
        parts[4] = urllib.urlencode(queryargs)
        newurl = urlparse.urlunparse(parts)

        return self.get(newurl, http=self._http)

    def __getitem__(self, key):
        """Translates slice notation on a `ListObject` instance into `limit`
        and `offset` filter parameters."""
        if isinstance(key, slice):
            # TODO: handle partial slice notation? there's a fuller implementation of this somewhere
            return self.filter(offset=key.start, limit=key.stop - key.start)

        try:
            getitem = super(ListObject, self).__getitem__
        except AttributeError:
            raise TypeError("'%s' object is unsubscriptable except by slices"
                % (type(self).__name__,))
        else:
            return getitem(key)
