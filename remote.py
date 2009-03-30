try:
    import json
except ImportError:
    # TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
    import simplejson as json

import httplib2
import httplib
import logging
from urlparse import urljoin, urlparse, urlunparse
from urllib import quote_plus
import types
from datetime import datetime
import time
import re

from remoteobjects.dataobject import DataObject, DataObjectMetaclass
from remoteobjects import fields

userAgent = httplib2.Http()

def omit_nulls(data):
    if not isinstance(data, dict):
        if not hasattr(data, '__dict__'):
            return str(data)
        data = dict(data.__dict__)
    for key in data.keys():
        # TODO: don't have etag in obj data in the first place?
        if data[key] is None or key == 'etag':
            del data[key]
    return data

class RemoteObject(DataObject):

    """A DataObject that can be fetched and put over HTTP through a REST
    API."""

    location_headers = {
        httplib.CREATED:           'Location',
        httplib.MOVED_PERMANENTLY: 'Location',
        httplib.FOUND:             'Location',
        httplib.OK:                'Content-Location',
        httplib.NOT_MODIFIED:      'Content-Location',
        httplib.NO_CONTENT:        None,
    }

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
        common cause of this status is an attempt to `PUT` a resource that has
        already changed on the server.

        """
        pass

    class BadResponse(httplib.HTTPException):
        """An HTTPException thrown when the client receives some other non-success
        HTTP response."""
        pass

    @classmethod
    def _raise_response(cls, response, url):
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

        try:
            location_header = cls.location_headers[response.status]
        except KeyError:
            # we only expect the statuses that have location headers defined
            raise cls.BadResponse('Unexpected response requesting %s %s: %d %s'
                % (classname, url, response.status, response.reason))

        if location_header is None:
            # then there's no content-type either, so we're done
            return

        if location_header.lower() not in response:
            raise cls.BadResponse(
                "%r header missing from %d %s response requesting %s %s"
                % (location_header, response.status, response.reason,
                   classname, url))

        # check that the response body was json
        if response.get('content-type') != 'application/json':
            raise cls.BadResponse(
                'Bad response fetching %s %s: content-type is %s, not JSON'
                % (classname, url, response.get('content-type')))

    def get_request(self, headers=None, **kwargs):
        if headers is None:
            headers = {}
        if 'accept' not in headers:
            headers['accept'] = 'application/json'

        # Use 'uri' because httplib2.request does.
        request = dict(uri=self._id, headers=headers)
        request.update(kwargs)
        return request

    @classmethod
    def get_response(cls, url, http=None, headers=None, **kwargs):
        # TODO: reconcile this with get_request... which is an instance method.
        logging.debug('Fetching %s' % (url,))

        if headers is None:
            headers = {}
        if 'accept' not in headers:
            headers['accept'] = 'application/json'

        if http is None:
            http = userAgent
        response, content = http.request(uri=url, headers=headers, **kwargs)
        cls._raise_response(response, url)
        logging.debug('Got content %s' % (content,))

        return response, content

    def update_from_response(self, response, content):
        """Adds the content of this HTTP response and message body to this RemoteObject.

        Use `update_from_response()` only when you would use
        `DataObject.update_from_dict()`: when decoding outside content (in
        this case an HTTP response) into an existing RemoteObject.

        """
        data = json.loads(content)
        self.update_from_dict(data)

        location_header = self.location_headers.get(response.status)
        if location_header is not None:
            self._id = response[location_header.lower()]

        if 'etag' in response:
            self._etag = response['etag']

    @classmethod
    def get(cls, url, http=None, **kwargs):
        """Fetches a RemoteObject from a URL.

        Parameter `url` is the URL from which the object should be gotten.
        Optional parameter `http` is the user agent object to use for
        fetching. `http` should be compatible with `httplib2.Http` objects.

        """
        response, content = cls.get_response(url, http)
        # Make a new instance and use update_from_response(), rather than
        # having a superfluous from_response() classmethod for this one call.
        self = cls()
        self.update_from_response(response, content)
        return self

    def post(self, obj, http=None):
        """Add another RemoteObject to this remote resource with a `POST`.

        Parameter `obj` is a RemoteObject to save to this RemoteObject's
        resource. For example, this (`self`) may be a collection to which you
        want to post an asset (`obj`).

        Optional parameter `http` is the user agent object to use for posting.
        `http` should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_id', None) is None:
            raise ValueError, 'Cannot add %r to %r with no URL to POST to' % (obj, self)

        body = json.dumps(obj.to_dict(), default=omit_nulls)
        response, content = obj.get_response(self._id, http=http,
            method='POST', body=body)
        obj.update_from_response(response, content)

    def put(self, http=None):
        """Save a RemoteObject to a remote resource.

        If the RemoteObject was fetched with a `get()` call, it is saved by
        HTTP `PUT` to the resource's URL. If the RemoteObject is new, it is
        saved through a `POST` to its parent collection.

        Optional `http` parameter is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_id', None) is None:
            raise ValueError, 'Cannot save %r with no URL to PUT to' % (self,)

        body = json.dumps(self.to_dict(), default=omit_nulls)

        headers = {}
        if hasattr(self, '_etag') and self._etag is not None:
            headers['if-match'] = self._etag

        response, content = self.get_response(self._id, http=http, method='PUT',
            body=body, headers=headers)
        logging.debug('Yay saved my obj, now turning %s into new content' % (content,))
        self.update_from_response(response, content)

    def delete(self, http=None):
        """Delete the remote resource represented by a RemoteObject.

        If the RemoteObject was fetched with a `get()` call, it is deleted
        through an HTTP `DELETE` to the resource's URL.

        Optional parameter `http` is the user agent object to use. `http`
        objects should be compatible with `httplib2.Http` objects.

        """
        if getattr(self, '_id', None) is None:
            raise ValueError, 'Cannot delete %r with no URL to DELETE' % (self,)

        headers = {}
        if hasattr(self, '_etag') and self._etag is not None:
            headers['if-match'] = self._etag

        response, content = self.get_response(self._id, http=http,
            method='DELETE', headers=headers)
        logging.debug('Yay deleted the obj, now... something something')

        # No more resource, no more URL.
        self._id = None
        del self._etag
