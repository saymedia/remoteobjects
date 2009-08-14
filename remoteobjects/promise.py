import urlparse
import urllib
import cgi

from remoteobjects.http import HttpObject
from remoteobjects.fields import Property


class PromiseError(Exception):
    """An exception representing an error promising or delivering a
    `PromiseObject` instance."""
    pass


class PromiseObject(HttpObject):
    """A `RemoteObject` that delays actual retrieval of the remote resource until
    required by the use of its data.

    A PromiseObject is only "promised" to the caller until its data is used.
    When the caller tries to use attributes that should have data in them from
    the remote resource, only *then* is the resource actually fetched.

    """

    def __init__(self, **kwargs):
        """Initializes a delivered, empty `PromiseObject`."""
        self._delivered = True
        self._http = None
        super(PromiseObject, self).__init__(**kwargs)

    def _get_api_data(self):
        if not self._delivered:
            self.deliver()
        return self.__dict__['api_data']

    def _set_api_data(self, value):
        self.__dict__['api_data'] = value

    def _del_api_data(self):
        del self.__dict__['api_data']

    api_data = property(_get_api_data, _set_api_data, _del_api_data)

    @classmethod
    def statefields(cls):
        return super(PromiseObject, cls).statefields() + ['_delivered']

    @classmethod
    def get(cls, url, http=None, **kwargs):
        """Creates a new undelivered `PromiseObject` instance that, when
        delivered, will contain the data at the given URL."""
        # Make a fake empty instance of this class.
        self = cls()
        self._location = url
        self._http = http
        self._delivered = False

        return self

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

    def update_from_dict(self, data):
        if not isinstance(data, dict):
            raise TypeError
        # Clear any local instance field data
        for k in self.fields.iterkeys():
            if k in self.__dict__:
                del self.__dict__[k]
        # Update directly to avoid triggering delivery.
        self.__dict__['api_data'] = data

    def update_from_response(self, url, response, content):
        """Fills the `PromiseObject` instance with the data from the given
        HTTP response and if successful marks the instance delivered."""
        super(PromiseObject, self).update_from_response(url, response, content)
        # Any updating from a response constitutes delivery.
        self._delivered = True

    def filter(self, **kwargs):
        """Returns a new undelivered `PromiseObject` instance, equivalent to
        this `PromiseObject` instance but further filtered by the given
        keyword parameters.

        By default, all filter parameters are added as parameters to the
        `PromiseObject` instance's query string.

        If your endpoint takes only certain parameters, or accepts parameters
        in some way other than query parameters in the URL, override this
        method to build the URL and return the new `PromiseObject` instance as
        you require.

        """
        parts = list(urlparse.urlparse(self._location))
        queryargs = cgi.parse_qs(parts[4], keep_blank_values=True)
        queryargs = dict([(k, v[0]) for k, v in queryargs.iteritems()])
        queryargs.update(kwargs)
        parts[4] = urllib.urlencode(queryargs)
        newurl = urlparse.urlunparse(parts)

        return self.get(newurl, http=self._http)


class ListObject(PromiseObject):

    """A `RemoteObject` representing a list of other `RemoteObject` instances.

    `ListObject` instances can be filtered by options that are passed to your
    target API, such as a list of recent objects or a search. Filtering a
    ListObject by a parameter returns a new copy of that ListObject that
    includes the new parameter.

    """

    def __getitem__(self, key):
        """Translates slice notation on a `ListObject` instance into ``limit``
        and ``offset`` filter parameters."""
        if isinstance(key, slice):
            args = dict()
            if key.start is not None:
                args['offset'] = key.start
                if key.stop is not None:
                    args['limit'] = key.stop - key.start
            elif key.stop is not None:
                args['limit'] = key.stop
            return self.filter(**args)

        try:
            getitem = super(ListObject, self).__getitem__
        except AttributeError:
            raise TypeError("'%s' object is unsubscriptable except by slices"
                % (type(self).__name__,))
        else:
            return getitem(key)
