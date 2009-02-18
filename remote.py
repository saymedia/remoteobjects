try:
    import json
except ImportError:
    # TODO: require 2.0+ version of simplejson that doesn't provide unicode keys
    import simplejson as json

import httplib2
import httplib
import logging
from urlparse import urljoin
import types
from datetime import datetime
import time
import re

from remoteobjects.dataobject import DataObject, DataObjectMetaclass

# TODO configurable?
BASE_URL = 'http://127.0.0.1:8000/'

userAgent = httplib2.Http()

class NotFound(httplib.HTTPException):
    pass

class Unauthorized(httplib.HTTPException):
    pass

class BadResponse(httplib.HTTPException):
    pass

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
        if callable(self.url):
            # Only give the url function the arguments it expects.
            import inspect
            if inspect.getargspec(self.url)[2] is not None:
                url = self.url(obj, **kwargs)
            else:
                url = self.url(obj)
        else:
            if getattr(obj, '_id') is None:
                raise ValueError, "The object must have an identity URL before you can follow its link"
            url = urljoin(obj._id, self.url)

        # Get the content.
        resp, content = RemoteObject.get_response(url, http=kwargs.get('http'))
        data = simplejson.loads(content)

        # Have our field decode it.
        j = self.fld.decode(data)

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

    @staticmethod
    def _raise_response(response, classname, url):
        # Turn exceptional httplib2 responses into exceptions.
        if response.status == httplib.NOT_FOUND: 
            raise NotFound('No such %s %s' % (classname, url))
        if response.status == httplib.UNAUTHORIZED:
            raise Unauthorized('Not authorized to fetch %s %s' % (classname, url))
        # catch other unhandled
        if response.status != httplib.OK:
            raise BadResponse('Bad response fetching %s %s: %d %s' % (classname, url, response.status, response.reason))
        if response.get('content-type') != 'application/json':
            raise BadResponse('Bad response fetching %s %s: content-type is %s, not JSON' % (classname, url, response.get('content-type')))

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
        cls._raise_response(response, classname=cls.__name__, url=url)
        logging.debug('Got content %s' % (content,))

        return response, content

    def update_from_response(self, response, content):
        data = json.loads(content)
        self.update_from_dict(data)
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
        self = cls()
        self.update_from_response(response, content)
        return self

    def post(self, obj, http=None):
        if getattr(self, '_id', None) is None:
            raise ValueError, 'Cannot add %r to %r with no URL to POST to' % (obj, self)

        body = json.dumps(obj.to_dict(), default=omit_nulls)
        response, content = self.get_response(self._id, http=http,
            method='POST', body=body)

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
        if hasattr(self, _etag) and self._etag is not None:
            headers['if-match'] = self._etag

        response, content = self.get_response(self._id, http=http, method='PUT',
            body=body, headers=headers)
        logging.debug('Yay saved my obj, now turning %s into new content' % (content,))
        self.update_from_response(response, content)
