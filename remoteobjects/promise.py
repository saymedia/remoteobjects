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

import urlparse
import urllib
import cgi

import httplib
import httplib2

import remoteobjects.http
from remoteobjects.fields import Property


class PromiseError(Exception):
    """An exception representing an error promising or delivering a
    `PromiseObject` instance."""
    pass


class PromisedResponse(httplib2.Response):
    def __init__(self, *args, **kwargs):
        self._delivered = True
        self._location = None
        self._http = None
        self._method = None
        super(PromisedResponse, self).__init__(*args, **kwargs)

    def __getattribute__(self, attr, *args):
        if (attr not in ('deliver', 'get_request', 'update_from_response')) and (attr.find('_') != 0):
            if not self._delivered:
                self.deliver()
        return super(PromisedResponse, self).__getattribute__(attr, *args)

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

        http = self._http
        if self._http is None:
            http = remoteobjects.http.userAgent

        request = self.get_request()
        response, content = http.request(**request)
        self.update_from_response(request['uri'], response, content)

    def get_request(self, url=None, headers=None, **kwargs):
        """Returns the parameters for requesting this `RemoteObject` instance
        as a dictionary of keyword arguments suitable for passing to
        `httplib2.Http.request()`.

        Optional parameter `headers` are also included in the request as HTTP
        headers. Other optional keyword parameters are also included as
        specified.

        """
        if url is None:
            url = self._location
        if headers is None:
            headers = {}

        # Use 'uri' because httplib2.request does.
        request = dict(uri=url, headers=headers, method=self._method)
        request.update(kwargs)
        return request

    def update_from_response(self, url, response, content=''):
        self._delivered = True
        super(PromisedResponse, self).__init__(response)

    def found(self):
        """Returns True when the HTTP is in the 200-299 range."""
        return 300 > self.status >= 200

    def can_delete(self):
        try:
            return self['allow'].find('DELETE') > -1
        except KeyError:
            return False


class PromiseObject(remoteobjects.http.HttpObject):
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
        self._get_kwargs = kwargs

        return self

    def head(self, http=None, **kwargs):
        """Creates a new undelivered `PromisedResponse` instance that, when
        delivered, will contain the HTTP Response for the given object."""

        resp = PromisedResponse({})
        resp._delivered = False
        resp._location = self._location
        resp._http = http
        resp._method = 'HEAD'
        return resp

    def options(self, http=None, **kwargs):
        """Creates a new undelivered `PromisedResponse` instance that, when
        delivered, will contain the HTTP Response for the given object."""

        resp = PromisedResponse({})
        resp._delivered = False
        resp._location = self._location
        resp._http = http
        resp._method = 'OPTIONS'
        return resp

    def __setattr__(self, name, value):
        if name is not '_delivered' and not self._delivered and name in self.fields:
            self.deliver()
        return super(PromiseObject, self).__setattr__(name, value)

    def __delattr__(self, name):
        if name is not '_delivered' and not self._delivered and name in self.fields:
            self.deliver()
        return super(PromiseObject, self).__delattr__(name)

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

        http = self._http
        if self._http is None:
            http = remoteobjects.http.userAgent

        request = self.get_request(**self._get_kwargs)
        response, content = http.request(**request)
        self.update_from_response(request['uri'], response, content)

    def update_from_dict(self, data):
        if not isinstance(data, dict):
            raise TypeError("Cannot update %r from non-dictionary data source %r"
                % (self, data))
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
