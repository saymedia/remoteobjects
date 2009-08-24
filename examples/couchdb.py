from datetime import datetime
import httplib
import simplejson as json
from urlparse import urljoin, urlparse

from remoteobjects import *


class Database(RemoteObject):
    pass


class CouchObject(RemoteObject):

    id        = fields.Field(api_name='_id')
    revision  = fields.Field(api_name='_rev')

    # CouchDB omits Locations for Created responses. Oops.
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


class ListItem(RemoteObject):

    id    = fields.Field()
    key   = fields.Field()
    value = fields.Field()


class CouchView(CouchObject, ListObject):

    total_rows = fields.Field()
    offset     = fields.Field()
    entries    = fields.List(fields.Object(ListItem), api_name='rows')

    def filter(self, **kwargs):
        for k, v in kwargs.iteritems():
            if isinstance(v, list) or isinstance(v, dict) or isinstance(v, bool):
                kwargs[k] = json.dumps(v)
        return super(CouchView, self).filter(**kwargs)
