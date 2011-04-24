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

import simplejson as json
from remoteobjects.json import ForgivingDecoder

import httplib2
import httplib
import logging

from remoteobjects.dataobject import DataObject, DataObjectMetaclass
from remoteobjects import fields

userAgent = httplib2.Http()

log = logging.getLogger('remoteobjects.http')


def omit_nulls(data):
    """Strips `None` values from a dictionary or `RemoteObject` instance."""
    if not isinstance(data, dict):
        if not hasattr(data, '__dict__'):
            return str(data)
        data = dict(data.__dict__)
    for key in data.keys():
        if data[key] is None:
            del data[key]
    return data


class HttpObject(DataObject):

    """A `DataObject` that can be fetched and put over HTTP through a RESTful
    JSON API."""

    response_has_content = {
        httplib.OK:                True,
        httplib.ACCEPTED:          False,
        httplib.CREATED:           True,
        httplib.NO_CONTENT:        False,
        httplib.MOVED_PERMANENTLY: True,
        httplib.FOUND:             True,
        httplib.NOT_MODIFIED:      True,
    }

    location_headers = {
        httplib.OK:                'Content-Location',
        httplib.CREATED:           'Location',
        httplib.MOVED_PERMANENTLY: 'Location',
        httplib.FOUND:             'Location',
    }

    location_header_required = {
        httplib.CREATED:           True,
        httplib.MOVED_PERMANENTLY: True,
        httplib.FOUND:             True,
    }

    content_types = ('application/json',)

    class NotFound(httplib.HTTPException):
        """An HTTPException thrown when the server reports that the requested
        resource was not found."""
        pass

    class Unauthorized(httplib.HTTPException):
        """An HTTPException thrown when the server reports that the requested
        resource is not available through an unauthenticated request.

        This exception corresponds to the HTTP status code 401. Thus when this
        exception is received, the caller may need to try again using the
        available authentication credentials.

        """
        pass

    class Forbidden(httplib.HTTPException):
        """An HTTPException thrown when the server reports that the client, as
        authenticated, is not authorized to request the requested resource.

        This exception corresponds to the HTTP status code 403. Thus when this
        exception is received, nothing the caller (as currently authenticated) can
        do will make the requested resource available.

        """
        pass

    class PreconditionFailed(httplib.HTTPException):
        """An HTTPException thrown when the server reports that some of the
        conditions in a conditional request were not true.

        This exception corresponds to the HTTP status code 412. The most
        common cause of this status is an attempt to ``PUT`` a resource that
        has already changed on the server.

        """
        pass

    class RequestError(httplib.HTTPException):
        """An HTTPException thrown when the server reports an error in the
        client's request.

        This exception corresponds to the HTTP status code 400.
        
        """
        pass

    class ServerError(httplib.HTTPException):
        """An HTTPException thrown when the server reports an unexpected error.

        This exception corresponds to the HTTP status code 500.

        """
        pass

    class BadResponse(httplib.HTTPException):
        """An HTTPException thrown when the client receives some other
        non-success HTTP response."""
        pass

    def __init__(self, **kwargs):
        self._location = None
        super(HttpObject, self).__init__(**kwargs)

    @classmethod
    def statefields(cls):
        return super(HttpObject, cls).statefields() + ['_location', '_etag']

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
        if 'accept' not in headers:
            headers['accept'] = ', '.join(self.content_types)

        # Use 'uri' because httplib2.request does.
        request = dict(uri=url, headers=headers)
        request.update(kwargs)
        return request

    @classmethod
    def raise_for_response(cls, url, response, content):
        """Raises exceptions corresponding to invalid HTTP responses that
        instances of this class can't be updated from.

        Override this method to customize the error handling behavior of
        `RemoteObject` for your target API. For example, if your API illegally
        omits ``Location`` headers from 201 Created responses, override this
        method to check for and allow them.

        """
        # Turn exceptional httplib2 responses into exceptions.
        classname = cls.__name__
        if response.status == httplib.NOT_FOUND:
            raise cls.NotFound('No such %s %s' % (classname, url))
        if response.status == httplib.UNAUTHORIZED:
            raise cls.Unauthorized('Not authorized to fetch %s %s' % (classname, url))
        if response.status == httplib.FORBIDDEN:
            raise cls.Forbidden('Forbidden from fetching %s %s' % (classname, url))
        if response.status == httplib.PRECONDITION_FAILED:
            raise cls.PreconditionFailed('Precondition failed for %s request to %s' % (classname, url))

        if response.status in (httplib.INTERNAL_SERVER_ERROR, httplib.BAD_REQUEST):
            if response.status == httplib.BAD_REQUEST:
                err_cls = cls.RequestError
            else:
                err_cls = cls.ServerError
            # Pull out an error if we can.
            content_type = response.get('content-type', '').split(';', 1)[0].strip()
            if content_type == 'text/plain':
                error = content.split('\n', 2)[0]
                exc = err_cls('%d %s requesting %s %s: %s'
                    % (response.status, response.reason, classname, url,
                       error))
                exc.response_error = error
                raise exc
            raise err_cls('%d %s requesting %s %s'
                % (response.status, response.reason, classname, url))

        try:
            response_has_content = cls.response_has_content[response.status]
        except KeyError:
            # we only expect the statuses that we know do or don't have content
            raise cls.BadResponse('Unexpected response requesting %s %s: %d %s'
                % (classname, url, response.status, response.reason))

        try:
            location_header = cls.location_headers[response.status]
        except KeyError:
            pass
        else:
            if cls.location_header_required.get(response.status) and location_header.lower() not in response:
                raise cls.BadResponse(
                    "%r header missing from %d %s response requesting %s %s"
                    % (location_header, response.status, response.reason,
                       classname, url))

        if not response_has_content:
            # then there's no content-type either, so we're done
            return

        # check that the response body was json
        content_type = response.get('content-type', '').split(';', 1)[0].strip()
        if content_type not in cls.content_types:
            raise cls.BadResponse(
                'Bad response fetching %s %s: content-type %s is not an expected type'
                % (classname, url, response.get('content-type')))

    def update_from_response(self, url, response, content):
        """Adds the content of this HTTP response and message body to this
        `RemoteObject` instance.

        Use `update_from_response()` only when you would use
        `DataObject.update_from_dict()`: when decoding outside content (in
        this case an HTTP response) into an existing `RemoteObject` instance.

        If the response is not a successful response from which the
        `RemoteObject` instance can be updated, an appropriate exception will
        be raised (as determined by the instance's `raise_from_response()`
        method).

        If the response includes a new location URL in the appropriate header
        (depending on the response status), the location of the `RemoteObject`
        instance is updated as well.

        """
        self.raise_for_response(url, response, content)

        if self.response_has_content.get(response.status):
            try:
                data = json.loads(content)
            except UnicodeDecodeError:
                data = json.loads(content, cls=ForgivingDecoder)

            self.update_from_dict(data)

        location_header = self.location_headers.get(response.status)
        if location_header is None:
            self._location = url
        elif self.location_header_required.get(response.status):
            self._location = response[location_header.lower()]
        else:
            self._location = response.get(location_header.lower(), url)

        if 'etag' in response:
            self._etag = response['etag']

    @classmethod
    def get(cls, url, http=None, **kwargs):
        """Fetches a new `RemoteObject` instance from a URL.

        Parameter `url` is the URL from which the object should be requested.
        Optional parameter `http` is the user agent object to use for
        fetching. `http` should be compatible with `httplib2.Http` instances.

        """
        self = cls()
        request = self.get_request(url=url, **kwargs)

        if http is None:
            http = userAgent
        response, content = http.request(**request)

        self.update_from_response(url, response, content)
        return self

    def post(self, obj, http=None):
        """Add another `RemoteObject` to this remote resource through an HTTP
        ``POST`` request.

        Parameter `obj` is a `RemoteObject` instance to save to this
        instance's resource. For example, this (`self`) may be a collection to
        which you want to post an asset (`obj`).

        Optional parameter `http` is the user agent object to use for posting.
        `http` should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_location', None) is None:
            raise ValueError('Cannot add %r to %r with no URL to POST to'
                % (obj, self))

        body = json.dumps(obj.to_dict(), default=omit_nulls)

        headers = {'content-type': self.content_types[0]}

        request = obj.get_request(url=self._location, method='POST',
            body=body, headers=headers)
        if http is None:
            http = userAgent
        response, content = http.request(**request)

        obj.update_from_response(self._location, response, content)

    def put(self, http=None):
        """Save a previously requested `RemoteObject` back to its remote
        resource through an HTTP ``PUT`` request.

        Optional `http` parameter is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_location', None) is None:
            raise ValueError('Cannot save %r with no URL to PUT to' % self)

        body = json.dumps(self.to_dict(), default=omit_nulls)

        headers = {}
        if hasattr(self, '_etag') and self._etag is not None:
            headers['if-match'] = self._etag
        headers['content-type'] = self.content_types[0]

        request = self.get_request(method='PUT', body=body, headers=headers)
        if http is None:
            http = userAgent
        response, content = http.request(**request)

        log.debug('Yay saved my obj, now turning %r into new content', content)
        self.update_from_response(self._location, response, content)

    def delete(self, http=None):
        """Delete the remote resource represented by the `RemoteObject`
        instance through an HTTP ``DELETE`` request.

        Optional parameter `http` is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_location', None) is None:
            raise ValueError('Cannot delete %r with no URL to DELETE' % self)

        headers = {}
        if hasattr(self, '_etag') and self._etag is not None:
            headers['if-match'] = self._etag

        request = self.get_request(method='DELETE', headers=headers)
        if http is None:
            http = userAgent
        response, content = http.request(**request)

        self.raise_for_response(self._location, response, content)

        log.debug('Yay deleted the remote resource, now disconnecting %r from it', self)

        # No more resource, no more URL.
        self._location = None
        try:
            del self._etag
        except AttributeError:
            # Don't mind if there's no etag.
            pass

    def head(self, http=None):
        """Issues a HTTP ``HEAD`` request for the object.

        Optional parameter `http` is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_location', None) is None:
            raise ValueError('Cannot issue HEAD for %r with no URL' % self)

        if http is None:
            http = userAgent
        response, content = http.request(uri=self._location, method='HEAD')

        return response

    def options(self, http=None):
        """Issues a HTTP ``OPTIONS`` request for the object.

        Optional parameter `http` is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        This method returns both the `HttpResponse` and content data.

        """
        if getattr(self, '_location', None) is None:
            raise ValueError('Cannot issue OPTIONS for %r with no URL' % self)

        if http is None:
            http = userAgent
        response, content = http.request(uri=self._location, method='OPTIONS')

        return response
