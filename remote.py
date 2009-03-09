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

# TODO configurable?
BASE_URL = 'http://127.0.0.1:8000/'

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

class Link(object):

    """A RemoteObject attribute that links from a source object to a related
    target object.

    For example, for an asset with comments, the comments list resource can be
    a `Link` from the asset with a type of `List(Comment)`. The asset is the
    source object and the comments list is the target object.

    Links are declared on the source class as attributes, but become callable
    methods. For example, if the Link is installed on `Asset` as `comments`,
    then `Asset.comments` will be the callable method that fetches that
    asset's comments list.

    """

    def __init__(self, url, fld):
        """Sets the Link's url and the type of resource at that URL.

        Parameter `url` is the URL from which the related resource can be
        fetched. If `url` is relative, it is interpreted as relative to the
        source object's URL.

        `url` can also be a callable function that returns the URL of the
        target resource, given either the source object or, if the function
        accepts variable keyword argument sets (`**kwargs`), the source object
        and the extra keyword arguments passed to the link method.

        Parameter `fld` is a Field that specifies how to decode the resource
        at the URL. For example, if the resource were itself an `Asset`
        object, `fld` would be a `fields.Object(Asset)`.

        """
        self.url = url
        self.fld = fld

    def _get_of_cls(self):
        return self.__dict__['of_cls']

    def _set_of_cls(self, of_cls):
        self.__dict__['of_cls'] = of_cls
        self.fld.of_cls = of_cls

    of_cls = property(_get_of_cls, _set_of_cls)

    def __call__(self, obj, **kwargs):
        """Fetches the remote resource the Link links to.

        Parameter `obj` is the existing related object (the asset object in
        the asset-comments example). Any other keyword arguments are passed to
        `RemoteObject.get()`, or if the Link's `url` is a callable function
        that accepts variable keyword argument sets, to the Link's `url`
        function too.

        """
        http = kwargs.get('http')
        if http is not None:
            del kwargs['http']

        if callable(self.url):
            # Only give the url function the arguments it expects.
            import inspect
            argument_names, vararg_name, varkw_name, defaults = inspect.getargspec(self.url)
            if varkw_name is not None:
                # Well, give it everything then.
                urlargs = kwargs
                kwargs = {}
                url = self.url(obj, **urlargs)
            else:
                # Only give the url function the kw arguments it'll take.
                urlargs = {}
                for argname in argument_names:
                    if argname in kwargs:
                        urlargs[argname] = kwargs[argname]
                        del kwargs[argname]
                url = self.url(obj, **urlargs)
        else:
            if getattr(obj, '_id') is None:
                raise ValueError, "The object must have an identity URL before you can follow its link"
            url = urljoin(obj._id, self.url)

        # Add remaining kwargs as query parameters.
        if kwargs:
            queryparts = []
            for k, v in kwargs.iteritems():
                if v is None:
                    continue
                # TODO: no one uses underscores in query parameters. that would be crazy.
                k = k.replace('_', '-')
                v = quote_plus(str(v))
                queryparts.append('%s=%s' % (k, v))
            if queryparts:
                query = '&'.join(queryparts)
                # Add it to the url, or to existing query params if present.
                parts = list(urlparse(url))
                if parts[4]:
                    parts[4] += '&' + query
                else:
                    parts[4] = query
                url = urlunparse(parts)

        # Get the content.
        response, content = RemoteObject.get_response(url, http=http)
        data = json.loads(content)

        # Have our field decode it.
        j = self.fld.decode(data)

        # Make sure the object knows where it came from.
        # TODO: refactor this against update_from_response somehow? ugh
        j._id = response['content-location']  # follow redirects
        if 'etag' in response:
            j._etag = response['etag']

        return j

class RemoteObjectMetaclass(DataObjectMetaclass):
    def __new__(cls, name, bases, attrs):
        # TODO: refactor with DataObjectMetaclass? urgh
        links = {}
        new_links = {}

        for base in bases:
            if isinstance(base, RemoteObjectMetaclass):
                links.update(base.links)

        for attrname, link in attrs.items():
            if isinstance(link, Link):
                new_links[attrname] = link
                # Replace the Link with a new method instead of deleting it.
                def make_method(linkobj):
                    def method(self, **kwargs):
                        return linkobj(self, **kwargs)
                    method.__name__ = attrname
                    return method
                attrs[attrname] = make_method(link)
            elif attrname in links:
                del links[attrname]

        links.update(new_links)
        attrs['links'] = links
        obj_cls = super(RemoteObjectMetaclass, cls).__new__(cls, name, bases, attrs)

        # Tell the link that this class owns it.
        for link in new_links.values():
            link.of_cls = obj_cls

        return obj_cls

class RemoteObject(DataObject):

    """A DataObject that can be fetched and put over HTTP through a REST
    API."""

    __metaclass__ = RemoteObjectMetaclass
    
    def __cmp__(self, obj):
        """Compare ids of API objects."""
        return cmp(self.id, obj.id)

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

        # catch other unhandled
        if response.status not in (httplib.OK, httplib.CREATED, httplib.NO_CONTENT):
            raise cls.BadResponse('Bad response fetching %s %s: %d %s' % (classname, url, response.status, response.reason))

        # check that the response body was json
        if response.get('content-type') and response.get('content-type') != 'application/json':
            raise cls.BadResponse('Bad response fetching %s %s: content-type is %s, not JSON' % (classname, url, response.get('content-type')))

    @classmethod
    def get_response(cls, url, http=None, headers=None, **kwargs):
        logging.debug('Fetching %s' % (url,))

        if headers is None:
            headers = {}
        if 'accept' not in headers:
            headers['accept'] = 'application/json'

        if http is None:
            http = userAgent
        response, content = http.request(url, headers=headers, **kwargs)
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
        # TODO: when is there ever no content-location? for unfollowed redirects?
        if 'content-location' in response:
            self._id = response['content-location']  # follow redirects
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
        response, content = self.get_response(self._id, http=http,
            method='POST', body=body)
        # TODO: wtf this is not a new object
        # obj.update_from_response(response, content)
        new_obj = obj.__class__()
        new_obj.update_from_response(response, content)
        return new_obj

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
        del self._id
        del self._etag
