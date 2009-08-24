import httplib
from optparse import OptionParser
import simplejson as json
import sys
from urlparse import urljoin, urlparse

from remoteobjects import RemoteObject, fields, ListObject


class CouchObject(RemoteObject):

    # CouchDB omits Locations for Created responses, so don't expect them.
    location_headers = dict(RemoteObject.location_headers)
    location_headers[httplib.CREATED] = None

    def update_from_response(self, url, response, content):
        if response.status == httplib.CREATED:
            # CouchDB CREATED responses don't contain full content, so only
            # unpack the ID and revision.
            data = json.loads(content)
            assert data['ok']
            self.update_from_created_dict(data)
            return

        try:
            super(CouchObject, self).update_from_response(url, response, content)
        except self.NotFound:
            # Count that as a delivery, too, since there was nothing to get.
            self._delivered = True
            raise

    def update_from_created_dict(self, data):
        pass


class Database(CouchObject):
    pass


class Document(CouchObject):

    id        = fields.Field(api_name='_id')
    revision  = fields.Field(api_name='_rev')

    def update_from_created_dict(self, data):
        self.id       = data['id']
        self.revision = data['rev']


class ListItem(RemoteObject):

    id    = fields.Field()
    key   = fields.Field()
    value = fields.Field()


class ViewResult(CouchObject, ListObject):

    total_rows = fields.Field()
    offset     = fields.Field()
    entries    = fields.List(fields.Object(ListItem), api_name='rows')

    def filter(self, **kwargs):
        for k, v in kwargs.iteritems():
            if isinstance(v, list) or isinstance(v, dict) or isinstance(v, bool):
                kwargs[k] = json.dumps(v)
        return super(ViewResult, self).filter(**kwargs)


class View(CouchObject):

    mapfn    = fields.Field(api_name='map')
    reducefn = fields.Field(api_name='reduce')


class Viewset(CouchObject):

    language = fields.Constant('javascript')
    views    = fields.Dict(fields.Object(View))


def create_db(url):
    db = Database.get(url)
    try:
        db.deliver()
    except Database.NotFound:
        db.put()
        print "Database %s created" % url
    else:
        print "Database %s already exists" % url


def create_view(dburl):
    viewset = Viewset.get(urljoin(dburl, '_design/profiles'))
    try:
        viewset.deliver()
        print "Retrieved existing 'profiles' views"
    except Viewset.NotFound:
        # Start with an empty set of views.
        viewset.views = {}

    profiles_url_code = """
        function (doc) {
            if (doc.class == 'profile')
                emit([doc.person], doc);
        }
    """
    viewset.views['url'] = View(mapfn=profiles_url_code)

    viewset.put()
    print "Updated 'profiles' views for %s" % dburl


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser()
    parser.add_option("-d", "--database", dest="database",
        help="URL of CouchDB database")
    opts, args = parser.parse_args()

    db = opts.database
    if db is None:
        print >>sys.stderr, "Option --database is required"
        return 1

    # Create the database, if necessary.
    create_db(db)

    # Create a view.
    create_view(db)

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
