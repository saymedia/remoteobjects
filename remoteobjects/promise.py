# Copyright (c) 2009 Six Apart Ltd.
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
        declared field of the instance's class, `__getattr__()` attempts to
        deliver the object before returning the value of that attribute.

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
        raise AttributeError('Instance %r has no such attribute %r'
            % (self, attr))

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
