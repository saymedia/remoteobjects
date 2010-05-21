#!/usr/bin/env python

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

"""

A generic example CouchDB client, implemented using remoteobjects.

"""

__version__ = '1.0'
__date__ = '24 August 2009'
__author__ = 'Mark Paschal'


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
