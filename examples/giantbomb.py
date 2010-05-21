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

An example Giant Bomb API client, implemented using remoteobjects.

"""

__version__ = '1.0'
__date__ = '24 August 2009'
__author__ = 'Mark Paschal'


from cgi import parse_qs
from datetime import datetime
from optparse import OptionParser
import sys
import time
from urllib import urlencode
from urlparse import urljoin, urlparse, urlunparse

from remoteobjects import RemoteObject, fields


class Bombject(RemoteObject):

    content_types = ('application/json', 'text/javascript')
    api_key = None

    @classmethod
    def get(cls, url, **kwargs):
        if not urlparse(url)[1]:
            url = urljoin('http://api.giantbomb.com/', url)

        self = super(Bombject, cls).get(url, **kwargs)
        self = self.filter(api_key=cls.api_key, format='json')
        return self

    def filter(self, **kwargs):
        url = self._location
        parts = list(urlparse(url))
        query = parse_qs(parts[4])
        query = dict([(k, v[0]) for k, v in query.iteritems()])

        for k, v in kwargs.iteritems():
            if v is None and k in query:
                del query[k]
            else:
                query[k] = v

        parts[4] = urlencode(query)
        url = urlunparse(parts)
        return super(Bombject, self).get(url)


class Image(Bombject):

    tiny_url = fields.Field()
    small_url = fields.Field()
    thumb_url = fields.Field()
    screen_url = fields.Field()
    super_url = fields.Field()


class Game(Bombject):

    id = fields.Field()
    name = fields.Field()
    api_detail_url = fields.Field()
    site_detail_url = fields.Field()

    summary = fields.Field(api_name='deck')
    description = fields.Field()
    image = fields.Object(Image)
    published = fields.Datetime(dateformat='%Y-%m-%d %H:%M:%S', api_name='date_added')
    updated = fields.Datetime(dateformat='%Y-%m-%d %H:%M:%S', api_name='date_last_updated')

    characters = fields.Field()
    concepts = fields.Field()
    developers = fields.Field()
    platforms = fields.Field()
    publishers = fields.Field()

    @classmethod
    def get(cls, url, **kwargs):
        res = GameResult.get(url)
        res = res.filter()
        return res.results[0]


class GameResult(Bombject):

    status_code = fields.Field()
    error = fields.Field()
    total = fields.Field(api_name='number_of_total_results')
    count = fields.Field(api_name='number_of_page_results')
    limit = fields.Field()
    offset = fields.Field()
    results = fields.List(fields.Object(Game))

    def update_from_dict(self, data):
        if not isinstance(data['results'], list):
            data = dict(data)
            data['results'] = [data['results']]
        super(GameResult, self).update_from_dict(data)


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = OptionParser()
    parser.add_option("-k", "--key", dest="key",
        help="your Giant Bomb API key")
    opts, args = parser.parse_args()

    if opts.key is None:
        print >>sys.stderr, "Option --key is required"
        return 1

    query = ' '.join(args)

    Bombject.api_key = opts.key

    search = GameResult.get('/search/').filter(resources='game')
    search = search.filter(query=query)

    if len(search.results) == 0:
        print "No results for %r" % query
    elif len(search.results) == 1:
        (game,) = search.results
        print "## %s ##" % game.name
        print
        print game.summary
    else:
        print "## Search results for %r ##" % query
        for game in search.results:
            print game.name

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
