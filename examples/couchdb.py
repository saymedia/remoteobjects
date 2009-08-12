try:
    import json
except ImportError:
    import simplejson as json

import httplib
from datetime import datetime
from urlparse import urljoin, urlparse

from django.conf import settings
from django.template.defaultfilters import slugify

from remoteobjects import *


class Database(RemoteObject):
    @classmethod
    def get(cls, url=None, http=None):
        if url is None:
            url = settings.COUCHDB_DATABASE
        return super(Database, cls).get(url, http)


class CouchObject(RemoteObject):
    id        = fields.Field(api_name='_id')
    revision  = fields.Field(api_name='_rev')

    # CouchDB improperly omits Locations for Created responses. Oops.
    location_headers = dict(RemoteObject.location_headers)
    location_headers[httplib.CREATED] = None

    def update_from_response(self, url, response, content):
        if response.status == httplib.CREATED:
            # CouchDB CREATED responses don't contain full content.
            data = json.loads(content)
            assert data['ok']
            self.id       = data['id']
            self.revision = data['rev']
            self._id = urljoin(settings.COUCHDB_DATABASE, self.id)
        else:
            super(CouchObject, self).update_from_response(url, response, content)

    @classmethod
    def get(cls, url, http=None, **kwargs):
        if not urlparse(url)[1]:
            url = urljoin(settings.COUCHDB_DATABASE, url)
        return super(CouchObject, cls).get(url, http=http, **kwargs)


class ListItem(RemoteObject):
    id    = fields.Field()
    key   = fields.Field()
    value = fields.Field()


class ViewlistMetaclass(ListObject.__metaclass__):

    @classmethod
    def makeMethod(cls, f):
        def fn(self, *args, **kwargs):
            if not self._delivered:
                self.deliver()
            return getattr(self.rows, f)(*args, **kwargs)
        fn.__name__ = f
        return fn

    def __new__(cls, name, bases, attr):
        for f in ('__len__ __setitem__ __delitem__ __iter__ __reversed__ append count index extend insert pop remove reverse sort'.split(' ')):
            attr[f] = cls.makeMethod(f)
        return super(ViewlistMetaclass, cls).__new__(cls, name, bases, attr)


class CouchView(CouchObject, ListObject):
    __metaclass__ = ViewlistMetaclass

    total_rows = fields.Field()
    offset     = fields.Field()
    rows       = fields.List(fields.Object(ListItem))

    def filter(self, **kwargs):
        for k, v in kwargs.iteritems():
            if isinstance(v, list) or isinstance(v, dict) or isinstance(v, bool):
                kwargs[k] = json.dumps(v)
        return super(CouchView, self).filter(**kwargs)

    def __getitem__(self, key):
        if self._delivered or not isinstance(key, slice):
            if not self._delivered:
                self.deliver()
            return self.rows.__getitem__(key)

        args = dict()
        if key.start is not None:
            args['offset'] = key.start
            if key.stop is not None:
                args['limit'] = key.stop - key.start
        elif key.stop is not None:
            args['limit'] = key.stop

        return self.filter(**args)


class TypedView(ViewlistMetaclass):
    def __new__(cls, name, bases=None, attr=None):
        if attr is None:
            # TODO: memoize me
            entryclass = name
            name = cls.__name__ + entryclass.__name__

            bases = (CouchView,)
            attr = {'rows': fields.List(SliceField('value', fields.Object(entryclass)))}
        return super(TypedView, cls).__new__(cls, name, bases, attr)


class SliceField(fields.Field):
    def __init__(self, key, fld, **kwargs):
        super(SliceField, self).__init__(**kwargs)
        self.key = key
        self.fld = fld

    def decode(self, value):
        value = value[self.key]
        return self.fld.decode(value)


class Asset(CouchObject):
    objclass  = fields.Constant('asset', api_name='class')
    title     = fields.Field()
    slug      = fields.Field()
    content   = fields.Field()
    published = fields.Datetime()
    updated   = fields.Datetime()
    tags      = fields.List(fields.Field())

    @classmethod
    def from_dict(cls, data):
        try:
            cls = cls.subclass_with_constant_field('kind', data['kind'])
        except ValueError:
            # Use existing class (probably Asset).
            pass

        ret = cls()
        ret.update_from_dict(data)
        return ret

    def to_dict(self):
        for dateattr in ('published', 'updated'):
            if self.__dict__.get(dateattr) is None:
                setattr(self, dateattr, datetime.now())
        if 'slug' not in self.__dict__ and 'title' in self.__dict__:
            self.slug = slugify(self.title)
        return super(Asset, self).to_dict()

    @classmethod
    def all(cls):
        try:
            kindfield = cls.fields['kind']
        except KeyError:
            startkey, endkey = ["Z"], []
        else:
            startkey, endkey = [kindfield.value, "Z"], [kindfield.value]

        l = TypedView(cls).get('_view/assets/kind')
        l = l.filter(descending=True, startkey=startkey, endkey=endkey)
        return l


class Link(Asset):
    kind = fields.Constant('link')
    url  = fields.Field()


class Image(Asset):
    kind   = fields.Constant('image')
    url    = fields.Field()
    height = fields.Field()
    width  = fields.Field()


class Post(Asset):
    kind = fields.Constant('post')


class Profile(CouchObject):
    person    = fields.Field()  # openid
    elsewhere = fields.Field()  # dict of stuff
