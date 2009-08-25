#!/usr/bin/env python

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


class Bombdate(fields.Field):

    timestamp_format = '%Y-%m-%d %H:%M:%S'

    def decode(self, value):
        try:
            return datetime(*(time.strptime(value, self.timestamp_format))[0:6])
        except ValueError:
            raise TypeError('Value to decode %r is not a valid date time stamp' % (value,))

    def encode(self, value):
        if not isinstance(value, datetime):
            raise TypeError('Value to encode %r is not a datetime' % (value,))
        if value.tzinfo is not None:
            raise TypeError("Value to encode %r is a datetime, but it has timezone information and we don't want to deal with timezone information" % (value,))
        return value.replace(microsecond=0).strftime(self.timestamp_format)


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
    published = Bombdate(api_name='date_added')
    updated = Bombdate(api_name='date_last_updated')

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
